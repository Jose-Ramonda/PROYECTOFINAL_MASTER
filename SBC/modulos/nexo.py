#   Archivo de librería intermedia entre libreria ramodbus 
#   Incluye funcion de API para encolar datos a enviar, funcion privada parser, hilo escucha cmd recibidos para parseo
#   Autor: José Ramonda
#   Ultima modificación: 10/7/2026

import queue
import time
import config
import main_mqtt

#Creo las colas del sistema

cola_entrada = queue.Queue() #Cola de entrada, que se parsea
cola_salida = {}    #arreglo (tupla) de colas, una por nodo, para enviar datos afuera
for id_nodo in config.NODOS_ID:
    cola_salida[id_nodo] = queue.Queue()

def encolar(id_nodo, comando, payload=b""):# Función pública, con la llamada a la API se envian datos para enviar comandos

    if id_nodo in cola_salida:
        # Armamos la estructura idéntica a la que espera tu hilo serial
        packet = {
            "cmd": comando,
            "payload": payload
        }
        cola_salida[id_nodo].put(packet)
        print(f"[LOGICA] Comando {comando} encolado para el nodo {hex(id_nodo)}")
    else:
        print(f"[LOGICA ERROR] El nodo {hex(id_nodo)} no existe en el sistema.")


def parser(evento):

    cmd = evento["cmd"]
    id_nodo = evento["id_nodo"]
    payload = evento["payload"]

    topico_nodo = f"sbc/status/{hex(id_nodo)}"
    # no uso switch case porque en  python no es muy intuitivo, lo ifeo todo
    if cmd == config.CMD_NFC:
        uid = payload.hex()
        print(f"[PARSER - NFC] Tarjeta leída en nodo {hex(id_nodo)}. UID: {uid}")
        # TODO: aca hacemos lo que hay que hacer
        

    elif cmd == config.CMD_DOOR:
        print(f"[PARSER - PUERTA] El nodo {hex(id_nodo)} reporta APERTURA DE LA PUERTA.")
        main_mqtt.publicar_mensaje(topico_nodo, "OK_PUERTA")

    elif cmd == config.CMD_READY:
        print(f"[PARSER - STATUS] El nodo {hex(id_nodo)} reporta que está listo.")
    
    elif cmd == config.CMD_WIFI:

        ip_detectada = ".".join(str(b) for b in payload)
        print(f"[PARSER - WIFI] El nodo {hex(id_nodo)} reporta IP: {ip_detectada}")
        main_mqtt.publicar_mensaje(topico_nodo, ip_detectada)

    elif cmd == config.CMD_TAKE_PH:
        main_mqtt.publicar_mensaje(topico_nodo,"OK_FOTO")
    
    else:
        print(f"[PARSER ALERTA] Comando {cmd} desconocido o no implementado.")


def nexo_task():#hilo uqe escucha y llama a parsear
    
    print("[LOGICA] Hilo de lógica intermedia iniciado y escuchando...")

    while True:
        try:
            # Se bloquea acá esperando que el hilo serial le mande algo.
            # El timeout de 1 segundo es para que el hilo no quede inmortal y pueda cerrarse con Ctrl+C
            evento = cola_entrada.get(timeout=1)
            
            # El hilo serial te puede mandar "DATOS_NODO" o alertas como "NODO_CAIDO"
            if "evento" in evento and evento["evento"] == "NODO_CAIDO":
                print(f"[LOGICA ALERTA] El nodo {hex(evento['id_nodo'])} se ha ido OFFLINE.")
                # TODO: Avisar a Telegram sobre la caída del nodo administrativo
            else:
                # Si no es una alerta del driver, es data cruda de un nodo: la pasamos al parser
                parser(evento)

        except queue.Empty:
            # No llegó nada en este segundo, volvemos a intentar (mantiene el bucle vivo)
            pass
