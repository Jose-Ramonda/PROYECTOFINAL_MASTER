#   Archivo principal que ejecuta bot de telegram
#   Autor: José Ramonda
#   Ultima modificación 11/7/2026


import botconfig
from telegram.ext import ApplicationBuilder
from mods import estados  # Importamos tu máquina de estados
from mods import MQTT

def main():
    #  Iniciamos la aplicación con el Token de botconfig.py
    app = ApplicationBuilder().token(botconfig.TELEGRAM_TOKEN).build()

    #  Le pedimos a estados.py la máquina ya armada y se la inyectamos al bot
    maquina_de_estados = estados.obtener_maquina_estados()
    app.add_handler(maquina_de_estados)
    MQTT.iniciar_escucha_notificaciones(app)
    
    print("[BOT] Servidor SBC escuchando peticiones en Telegram...")

    #  Encendemos el motor de escucha
    print("[BOT] Servidor SBC escuchando peticiones en Telegram...")
    app.run_polling()

if __name__ == '__main__':
    main()