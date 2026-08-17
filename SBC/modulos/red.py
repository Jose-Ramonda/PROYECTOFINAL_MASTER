import subprocess
import socket
from modulos.nexo import encolar
import config
import math
import time



# Constantes de subcomandos de flujo de wifi
TIPO_SSID = 1 # WIFI_CHNG_SSID_MSJ
TIPO_PASS = 2 # WIFI_CHNG_PASS_MSJ
TIPO_WIFI_ON = 0 #encender wifi


# --- 1. EXTRAER NOMBRE DE LA RED ---
def obtener_nombre_wifi_activa():
    try:
        # -t (terse) da una salida limpia para scripts
        # -f NAME,TYPE pide solo nombre de la conexión y el tipo
        # --active filtra para mostrar solo las que están levantadas
        comando = "nmcli -t -f NAME,TYPE connection show --active"
        salida = subprocess.check_output(comando, shell=True, text=True).strip()
        
        for linea in salida.split('\n'):
            # Buscamos la línea que termina con el tipo de red Wi-Fi
            if linea.endswith('802-11-wireless'):
                # Hacemos split desde la derecha (rsplit) por si el nombre de red tiene dos puntos
                nombre_red = linea.rsplit(':', 1)[0]
                return nombre_red
                
        print("[NET AUTO] No hay ninguna red Wi-Fi conectada actualmente.")
        return None
        
    except subprocess.CalledProcessError as e:
        print(f"[NET AUTO ERROR] Falló la consulta a nmcli: {e}")
        return None

# --- 2. EXTRAER CONTRASEÑA ---
def extraer_credenciales_wifi(nombre_red):
    try:
        comando_psk = f"sudo nmcli -s -g 802-11-wireless-security.psk connection show '{nombre_red}'"
        password = subprocess.check_output(comando_psk, shell=True, text=True).strip()
        
        if not password:
            return None
        return password
    except subprocess.CalledProcessError:
        return None

# --- 3. OBTENER IP DEL SERVIDOR ---
def obtener_ip_sbc():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# ==========================================
# LA FUNCIÓN RECOLECTORA FINAL
# ==========================================
def obtener_datos_red_completos():
    """
    Rejunta SSID, Password e IP de forma 100% automática.
    Retorna (ssid, password, ip) o (None, None, None) si falla.
    """
    print("[NET] Analizando entorno de red...")
    
    ssid = obtener_nombre_wifi_activa()
    if not ssid:
        return None, None, None
        
    password = extraer_credenciales_wifi(ssid)
    if not password:
        print(f"[NET] No se pudo obtener la clave para {ssid}")
        return None, None, None
        
    ip_sbc = obtener_ip_sbc()
    
    print(f"[NET] -> ÉXITO: SSID='{ssid}' | IP='{ip_sbc}'")
    print(f"PASSWORD: {password}")
    return ssid, password, ip_sbc

def despachar_url_servidor(ip_servidor, puerto=1880):
    """
    Convierte la IP y el puerto a 6 bytes y los encola para todos los nodos.
    """
    try:
        # 1. Convertimos la IP string ("192.168.136.91") a 4 bytes
        # Separamos por los puntos y creamos un array de enteros
        partes_ip = ip_servidor.split('.')
        ip_bytes = bytes([int(p) for p in partes_ip])
        
        # 2. Convertimos el puerto a 2 bytes en Little Endian (88, 7)
        puerto_bytes = puerto.to_bytes(2, byteorder='little')
        
        # 3. Concatenamos para crear el payload final de 6 bytes
        payload_server = ip_bytes + puerto_bytes
        
        # 4. Barremos el array de Nodos usando el for
        for id_nodo in config.NODOS_ID:
            encolar(id_nodo, config.CMD_URL, payload_server)
            
        print(f"[NET CFG] IP {ip_servidor}:{puerto} despachada a todos los nodos.")
        
    except Exception as e:
        print(f"[NET CFG ERROR] Fallo al armar la trama de IP: {e}")




def despachar_credenciales_chunks(ssid, password):
    """
    Toma las credenciales, las divide en pedazos de hasta 7 caracteres 
    y encola las tramas con la cabecera de 3 bytes para FreeRTOS.
    """


    MAX_PAYLOAD = 10
    HEADER_SIZE = 3
    MAX_DATA = MAX_PAYLOAD - HEADER_SIZE # Quedan 7 bytes libres para texto

    def encolar_texto(tipo, texto):
        texto_bytes = texto.encode('utf-8')
        total_bytes = len(texto_bytes)
        
        # Calculamos cuántos pedazos necesitamos en total
        total_chunks = math.ceil(total_bytes / MAX_DATA)
        if total_chunks == 0: 
            return # Evitamos procesar strings vacíos
            
        for id_nodo in config.NODOS_ID:
            for i in range(total_chunks):
                chunk_actual = i + 1 # FreeRTOS espera que empiece a contar desde el 1
                
                # Recortamos el pedazo de string correspondiente
                inicio = i * MAX_DATA
                fin = inicio + MAX_DATA
                chunk_datos = texto_bytes[inicio:fin]
                
                # Armamos el array de bytes: [Tipo, Actual, Total] + Datos
                cabecera = bytes([tipo, chunk_actual, total_chunks])
                payload_final = cabecera + chunk_datos
                
                # Encolamos con tu comando maestro de red
                # Asumo que config.CMD_WIFI es el comando principal para este buffer
                encolar(id_nodo, config.CMD_WIFI, payload_final)
                
    # 1. Encolamos el SSID
    encolar_texto(TIPO_SSID, ssid)
    
    # 2. Encolamos la contraseña
    encolar_texto(TIPO_PASS, password)
    
    # 3. Encolamos el comando de conectar (Prender Wi-Fi)
    # Según tu C, el TIPO 3 es WIFI_PRENDER_MSJ
    for id_nodo in config.NODOS_ID:
        encolar(id_nodo, config.CMD_WIFI, bytes([TIPO_WIFI_ON, 1, 1])) 
        
    print(f"[NET CFG] Credenciales despachadas en {MAX_DATA} bytes por trama.")



def hacer_ping(ip):
    """Ejecuta un ping rápido de 1 solo paquete a nivel sistema operativo."""
    comando = f"ping -c 1 -W 2 {ip}"
    try:
        res = subprocess.run(comando, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def net_monitor_task(func_encolar):
    """
    Hilo monitor simple: revisa el diccionario de config, 
    hace ping a cada IP registrada y reconecta si falla.
    """
    print("[NET MONITOR] Hilo monitor de red iniciado...")
    
    # Control de fallos consecutivos por nodo para evitar falsos positivos
    fallos_consecutivos = {}

    while True:
        
        
        # Si el diccionario está vacío, salteamos la ronda
        if not config.ips_nodos:
            continue
            
        # Iteramos sobre una copia de los ítems para evitar errores si el diccionario cambia mientras se lee
        for id_nodo, ip in list(config.ips_nodos.items()):
            
            if hacer_ping(ip):
                # Si responde, reseteamos sus fallos
                fallos_consecutivos[id_nodo] = 0
            else:
                # Suma un fallo
                fallos_consecutivos[id_nodo] = fallos_consecutivos.get(id_nodo, 0) + 1
                
                # Si acumula 3 fallos seguidos, mandamos a reconectar
                if fallos_consecutivos[id_nodo]  >= 3:
                    print(f"[NET ALERT] Nodo {hex(id_nodo)} perdido. Forzando reconexión Wi-Fi...")
                    
                    # Trama de reconexión según tu FreeRTOS: Tipo 0 (WIFI_PRENDER_MSJ), Chunk 1, Total 1
                    payload_reconexion = bytes([TIPO_WIFI_ON, 1, 1])
                    
                    # Usamos la función encolar 
                    func_encolar(id_nodo, config.CMD_WIFI, payload_reconexion)
                    
                    # Reseteamos el contador para darle tiempo a que vuelva a conectar
                    fallos_consecutivos[id_nodo] = 0
        #Espera un minuto entre pings, es un monitoreo lento
        time.sleep(60)



# ejecutar para probar:
if __name__ == "__main__":
    s, p, i = obtener_datos_red_completos()
    if s:
        print("Todo listo para empaquetar y enviar al ESP32.")