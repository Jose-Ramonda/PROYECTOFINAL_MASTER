#   Módulo MQTT Unificado para el Bot de Telegram
#   Autor: José Ramonda
#   Fecha: 13/7/2026

import os
import json
import asyncio
import paho.mqtt.client as mqtt
from telegram import Bot  # Importación directa para v20+
import botconfig  # Contiene MQTT_BROKER, MQTT_PORT, TOKEN y DICCIONARIO_NODOS

# Inicializamos el cliente de bot aislado para el hilo de MQTT de notificaciones
_bot_inyector = Bot(token=botconfig.TELEGRAM_TOKEN)

# ----------------------------------------------------
# 1. ENVIAR COMANDOS AL MAIN PARA QUE LOS RECIBA LA ESP
# ----------------------------------------------------
def publicar_comando(accion, payload):
    """Publica el comando en sbc/cmd/accion y se desconecta de inmediato"""
    try:
        cliente = mqtt.Client()
        cliente.connect(botconfig.MQTT_BROKER, botconfig.MQTT_PORT, keepalive=60)
        
        topico = f"sbc/cmd/{accion}"
        publicacion = cliente.publish(topico, payload, qos=1)
        publicacion.wait_for_publish(timeout=2.0)
        
        cliente.disconnect()
        print(f"[BOT-MQTT SUCCESS] Publicado en {topico} -> {payload}")
        return True
    except Exception as e:
        print(f"[BOT-MQTT ERROR] Falló la publicación: {e}")
        return False


## ----------------------------------------------------
# 2. LISTENER DE NOTIFICACIONES (NODE-RED -> BOT)
# ----------------------------------------------------
async def enviar_directo_sincrono(chat_id, evento, nombre_nodo, data):
    """Abre el canal de red de Telegram, despacha Texto o Foto según el evento y cierra"""
    async with _bot_inyector:
        try:
            # Caso 1: Confirmación de apertura de puerta (Texto plano)
            if evento == "puerta_ok":
                texto = f"Confirmado: El acceso {nombre_nodo} ha sido abierto de forma correcta."
                await _bot_inyector.send_message(chat_id=chat_id, text=texto)
                
            # Caso 2: clonacion de credenciales
            elif evento == "alerta":
                # data contiene el nombre del titular afectado (ej: "Jose Ramonda")
                texto = (
                    f"¡ALERTA CRITICA DE SEGURIDAD!\n\n"
                    f"Se ha detectado un intento de acceso con una tarjeta CLONADA.\n"
                    f"Titular: {data}\n"
                    f"Acceso: {nombre_nodo}\n\n"
                    f"La tarjeta implicada ha sido BLOQUEADA en el sistema automáticamente."
                )
                await _bot_inyector.send_message(chat_id=chat_id, text=texto)
            # Caso 3: Foto de control solicitada por un usuario (Imagen + Epígrafe)
            elif evento == "foto_solicitada_ok":
                if os.path.exists(data):
                    with open(data, 'rb') as foto:
                        await _bot_inyector.send_photo(
                            chat_id=chat_id, 
                            photo=foto, 
                            caption=f"Captura de control solicitada para {nombre_nodo}."
                        )
                else:
                    texto = f"Error: Archivo no encontrado para la foto solicitada en {nombre_nodo}."
                    await _bot_inyector.send_message(chat_id=chat_id, text=texto)
                    
            # Caso 4: Alerta espontánea por Timbre físico (Imagen + Epígrafe)
            elif evento == "foto_espontanea_ok":
                if os.path.exists(data):
                    with open(data, 'rb') as foto:
                        await _bot_inyector.send_photo(
                            chat_id=chat_id, 
                            photo=foto, 
                            caption=f"Alerta: Estan tocando el timbre en {nombre_nodo}."
                        )
                else:
                    texto = f"Alerta: Estan tocando el timbre en {nombre_nodo} (Fotografia no disponible)."
                    await _bot_inyector.send_message(chat_id=chat_id, text=texto)

            # Caso 5: Errores de hardware reportados desde Node-RED
            elif evento == "foto_error":
                texto = f"Alerta de hardware en {nombre_nodo}: Fallo el disparo de la camara.\nDetalle: {data}"
                await _bot_inyector.send_message(chat_id=chat_id, text=texto)

            elif evento == "timbre_sin_foto":
                texto = f"Alerta: Estan tocando el timbre en {nombre_nodo} (Fallo la carga de la imagen)."
                await _bot_inyector.send_message(chat_id=chat_id, text=texto)

        except Exception as e_envio:
            print(f"[BOT-MQTT ERROR] Error en send_message/photo para chat {chat_id}: {e_envio}")


def _on_message_notificaciones(client, userdata, msg):
    """Callback lineal de Paho MQTT (Hilo secundario de escucha)"""
    try:
        payload_dict = json.loads(msg.payload.decode("utf-8"))
        
        destino = payload_dict["destino"]
        evento = payload_dict["evento"]
        id_nodo = payload_dict["nodo"]  
        data = payload_dict["data"]  # Contiene la ruta absoluta del archivo o string de error
        
        # Traducimos la ID del nodo al string legible guardado en botconfig.py
        nombre_nodo = botconfig.DICCIONARIO_NODOS.get(id_nodo, id_nodo)
        print(f"[BOT-MQTT IN] Evento: {evento.upper()} | Nodo: {nombre_nodo} | Destino: {destino}")
        
        # Lista de eventos válidos que sabe procesar nuestro despachador
        eventos_validos = ["puerta_ok", "foto_solicitada_ok", "foto_espontanea_ok", "foto_error", "timbre_sin_foto", "alerta"]
        if evento not in eventos_validos:
            return  # Ignoramos eventos desconocidos o mal formateados

        # Ejecutamos el envío levantando el mini-loop exclusivo de asyncio para este hilo
        if destino == "all":
            from . import auth
            datos_credenciales = auth.cargar_datos()
            for usuario, datos in datos_credenciales.get("usuarios", {}).items():
                user_id_dinamico = datos.get("user_id")
                if user_id_dinamico:
                    asyncio.run(enviar_directo_sincrono(int(user_id_dinamico), evento, nombre_nodo, data))
        else:
            asyncio.run(enviar_directo_sincrono(int(destino), evento, nombre_nodo, data))
            
        print("[BOT-MQTT SUCCESS] Operacion despachada a Telegram correctamente.")

        # --- LIMPIEZA ABSOLUTA DEL DISCO ---
        # Si el evento involucraba una foto real y el archivo todavía está asentado en el disco,
        # lo borramos ACÁ (afuera del bucle de usuarios) para garantizar que la próxima vuelta sea fresca.
        if evento in ["foto_solicitada_ok", "foto_espontanea_ok"] and os.path.exists(data):
            try:
                os.remove(data)
                print(f"[BOT-MQTT] Archivo temporal eliminado de forma segura: {data}")
            except Exception as e_borrado:
                print(f"[BOT-MQTT ERROR] No se pudo eliminar el archivo físico: {e_borrado}")

    except Exception as e:
        print(f"[BOT-MQTT ERROR] Falló el procesamiento de la notificación en callback: {e}")


def iniciar_escucha_notificaciones(app_telegram=None):
    """Inicializa el hilo de fondo para oír las alertas de Node-RED"""
    cliente = mqtt.Client()
    cliente.on_message = _on_message_notificaciones
    
    try:
        cliente.connect(botconfig.MQTT_BROKER, botconfig.MQTT_PORT, keepalive=60)
        # Suscripción al tópico rústico unificado sbc/notify
        cliente.subscribe("sbc/notify", qos=1)
        cliente.loop_start()
        print("[BOT-MQTT] Escuchador de notificaciones acoplado en 'sbc/notify'")
    except Exception as e:
        print(f"[BOT-MQTT ERROR] No se pudo iniciar el listener de fondo: {e}")