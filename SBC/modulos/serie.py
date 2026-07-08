#   Archivo de librería de interfaz serial del protocolo Ramobdbus
#   Autor: José Ramonda
#   Ultima modificación: 8/7/2026

import threading
import serial
import struct
import time
import queue
from . import config


ser = None #Creo el objeto serial global, lo incializo luego

def crc16_esp(data: bytes, seed=0xFFFF):
    crc = (~seed) & 0xFFFF   # igual que en ROM

    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
            crc &= 0xFFFF

    return (~crc) & 0xFFFF

def sender(id, cmd, payload):   #Funcion que manda comandos 
    
    header = struct.pack('BBB', id, cmd, len(payload))
    crc = crc16_esp(header + payload)

    trama = (
            struct.pack('B', config.START_BYTE)
            + header
            + payload
            + struct.pack('<H', crc)
        )
    ser.write(trama)

def listener():
    byte = ser.read(1)

    if not byte:
        return None # Si hay timeout devuelvo None -> error
    
    # Extraemos el valor numérico con [0] para comparar con la macro
    if byte[0] != config.START_BYTE:
        return None    

    id = ser.read(1) # Leo encabezado

    if not id:
        return None
    
    if id[0] != config.MASTER_ID:
        return None

    cmd = ser.read(1)
    if not cmd:
        return None


    sz = ser.read(1)
    if not sz:
        return None
    
    payload = b"" # Inicializamos el payload vacío por defecto
    if sz[0] > 0:
        payload = ser.read(sz[0])
        if len(payload) != sz[0]:
            return None
            
    crc_recibido = ser.read(2)
    if len(crc_recibido) < 2:
        return None
    
    # Desempaquetamos el CRC recibido (Little Endian)
    crc = struct.unpack('<H', crc_recibido)[0]

    crc_calculado = crc16_esp(id + cmd + sz + payload) #Aca me complica el payload
    
    if crc != crc_calculado:
        return None

    return cmd[0], payload



def comunicacion(cola_salida, cola_entrada):    

    #cola entrada es una cola que envia los datos recibidos al parser en el otro hilo
    #cola salida es un diccionario con cada cola de cada comando que se quiera mandar a cada nodo

    #inicio la comunicación serie
    global ser
    ser = serial.Serial(
        port=config.PORT,  # cambiar si hace falta
        baudrate=config.BAUD_RATE,
        timeout= config.SERIAL_TIMEOUT
    )

    #Creo los status de los nodos
    estados_nodos = {}  #Diccionario
    for id_nodo in config.NODOS_ID:
        estados_nodos[id_nodo] = {
            "status": "ONLINE",
            "n_retry": 0,
            "last": time.time()
        }   #Lleno con status
    


    while True:     
        #Aca hacemos el polling
        indata = {
            "cmd" : 0,
            "payload" : None
        }
        data = {
            "cmd" : 0,
            "payload" : None
        }

        for id_nodo in config.NODOS_ID:
            if estados_nodos[id_nodo]["status"] == "ONLINE":    #Si el nodo anda
                #Mando el pollin/comando
                try:
                    data = cola_salida[id_nodo].get_nowait() #Si hay algo para mandar
                    sender(id_nodo,data["cmd"] ,data["payload"]) #pues lo mando
                except queue.Empty:
                    sender(id_nodo,config.CMD_POLL ,"") #Si la cola de ese nodo está vacía, mando un polling
                #Ahora recibo
                res = listener() # intento recibir respuesta
                if res == None:
                    estados_nodos[id_nodo]["n_retry"] +=1   #si falla subo
                    if estados_nodos[id_nodo]["n_retry"] >= config.MAX_REINTENTOS:  #me fijo aca para no hacer comparaciones en flujo normal
                        estados_nodos[id_nodo]["n_retry"] = 0
                        estados_nodos[id_nodo]["status"] = "OFFLINE"
                        #TODO aca mandar afuera un aviso, ver despues
                        estados_nodos[id_nodo]["last"] = time.time()#esto no se si usarlo o mandar diagnostico a demanda, queda en veremos
                else:   #si llega bien
                    indata["cmd"],indata["payload"] = res
                    if indata["cmd"] == config.CMD_ACK: #si es un miserable ACK
                        continue #no hago nada
                    elif indata["cmd"] == config.CMD_NACK and data["cmd"] !=0: #si legó mal, y lo que mande no era un polling
                        cola_salida[id_nodo].put(data)  #vuelvo a encolar para el otro siclo
                    else:
                        cola_entrada.put(indata)
            elif estados_nodos[id_nodo]["status"] == "OFFLINE":
                continue
            time.sleep(config.POLLING_TIME)
            #TODO ver reconexiones
