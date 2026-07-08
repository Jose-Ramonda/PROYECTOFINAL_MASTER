#   Archivo de librería intermedia entre libreria ramodbus 
#   Autor: José Ramonda
#   Ultima modificación: 8/7/2026

import queue
import time
from . import config

# Función global/pública para que CUALQUIER módulo futuro envíe comandos
def enviar_comando_a_nodo(cola_salida, id_nodo, comando, payload=b""):

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


def parser_data_nodo(evento):

    cmd = evento["cmd"]
    id_nodo = evento["id_nodo"]
    payload = evento["payload"]


    # Aquí mapeas las acciones según tus macros de config.py
    if cmd == config.CMD_NFC:
        uid = payload.hex()
        print(f"[PARSER - NFC] Tarjeta leída en nodo {hex(id_nodo)}. UID: {uid}")
        # TODO: Aquí llamarías a la validación de base de datos SQLite en el futuro.
        # Si la BD dice OK -> enviar_comando_a_nodo(..., id_nodo, config.CMD_DOOR)

    elif cmd == config.CMD_WIFI:
        print(f"[PARSER - WIFI] El nodo {hex(id_nodo)} reporta estado de su conexión.")

    elif cmd == config.CMD_READY:
        print(f"[PARSER - STATUS] El nodo {hex(id_nodo)} reporta que está listo.")

    else:
        print(f"[PARSER ALERTA] Comando {cmd} desconocido o no implementado.")


def hilo_logica(cola_entrada, cola_salida):
    """
    Bucle principal del hilo de lógica intermedia.
    Escucha de forma eficiente todo lo que el hilo serial tira en cola_entrada.
    """
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
                parser_data_nodo(evento)

        except queue.Empty:
            # No llegó nada en este segundo, volvemos a intentar (mantiene el bucle vivo)
            pass