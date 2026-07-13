#   Archivo de configuración del bot de telegram
#   Autor: José Ramonda
#   Última modificación : 11/7/2026


# --- CONFIGURACIÓN DE RED Y TELEGRAM ---
TELEGRAM_TOKEN = "8641641720:AAFUqesv-oLSnOYNmCaWURIiwv6KQYu2RpA"

# Parámetros MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_BASE_TOPIC = "sbc/cmd"

#Nodos
DICCIONARIO_NODOS = {
    "0x0A": "Acceso Frente",
    "0x14": "Acceso Patio",
    "0x1E": "Acceso Bicicletero"
}