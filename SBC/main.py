#   Archivo principal que corre los hilos de cada módulo del sistema
#   Autor: José Ramonda
#   Ultima modificación: 10/7/2026

import threading
import time
import sys

# Importo tareas
import config
from modulos.nexo import nexo_task
from modulos.nexo import cola_entrada, cola_salida
from modulos.nexo import encolar
from modulos.serie import comunicacion_task

def main():
    print("==================================================")
    print("=                     Iniciando                  =")
    print("==================================================")

    #Crear objeto hilo para la tarea nexo (parser)
    hilo_nexo = threading.Thread(target=nexo_task, daemon=True)

    #Crear objeto hilo para la tarea comunicacion (polling)
    hilo_serial = threading.Thread(
        target=comunicacion_task, 
        args=(cola_salida, cola_entrada), 
        daemon=True
    )

    #daemon True => los hilos son sub hilos del main, si pongo false y termino el programa main siguen andadno y tengo que matarlos por terminal
    # Lanzo los hilos
    print("[MAIN] Lanzando hilos de ejecución...")
    hilo_nexo.start()
    hilo_serial.start()
    print("[MAIN] Hilos corriendo. Sistema operativo en escucha.")

    time.sleep(5)
    encolar(0x0A,config.CMD_DOOR,b"")
    # Bucle infinito del hilo principal para poder cerrarlo por teclado
    try:
        while True:
            time.sleep(1)  # Bloqueo de 1 segundo
            
    except KeyboardInterrupt:
        # con Ctrl +C cierro el proceso
        print("\n[MAIN] Interrupción detectada. Cerrando Servidor SBC...")
        sys.exit(0)

if __name__ == "__main__":
    main()