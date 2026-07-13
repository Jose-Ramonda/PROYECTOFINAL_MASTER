#   Módulo de Comunicación MQTT para el Proceso Principal (SBC Hardware)
#   Autor: José Ramonda
#   Modificado: 13/7/2026

#   Módulo MQTT Rústico de Control
#   Autor: José Ramonda
#   Fecha: 13/7/2026

import paho.mqtt.client as mqtt
import config
import nexo

#Funcion de publicacion local
def publicar_mensaje(topico, payload):
    """Se conecta, escupe el mensaje y se desconecta al instante"""
    try:
        cliente = mqtt.Client()
        cliente.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
        
        info = cliente.publish(topico, payload, qos=1)
        info.wait_for_publish() # Esperamos que impacte en el broker
        
        cliente.disconnect()
        print(f"[MQTT PUB SUCCESS] {topico} -> {payload}")
        return True
    except Exception as e:
        print(f"[MQTT PUB ERROR] No se pudo publicar: {e}")
        return False


#Listener
def _on_message(client, userdata, msg):
    """El switch-case donde derivás cada acción según el tópico"""
    topico = msg.topic
    payload_crudo = msg.payload.decode("utf-8") # Recibe: "0x0A,987654321"
    
    # Si el payload contiene una coma, lo podamos para quedarnos solo con el nodo
    if "," in payload_crudo:
        nodo = payload_crudo.split(",")[0] # Se queda con "0x0A"
    else:
        nodo = payload_crudo # Por si acaso llega un mensaje viejo sin chat_id
    # Convertimos los bytes del payload a string para operar cómodos
    
    
    # --- ACÁ ESTÁ TU SWITCH-CASE ---
    if topico == "sbc/cmd/abrir":
        print(f"[ACCION] Ejecutando apertura del nodo {nodo} por bus serie...")
        nexo.encolar(nodo,config.CMD_DOOR,b"")
        
    elif topico == "sbc/cmd/foto":
        print(f"[ACCION] Encolando pedido de fotografia para el nodo {nodo}...")
        nexo.encolar(nodo,config.CMD_TAKE_PH,b"")
        
    elif topico == "sbc/nodo/ip_solicitud":
        # Por si el bot te pide la IP de un nodo en caliente
        print(f"[ACCION] Bot solicita IP. Buscando y respondiendo...")
        # ip_encontrada = nexo.obtener_ip_nodo(payload)
        # publicar_mensaje("sbc/nodo/ip_respuesta", ip_encontrada)
        
    elif topico == "sbc/evt/foto_lista":
        print(f"[ACCION] Node-RED avisa que guardó la foto {nodo}. Avisando al bot...")
        # publicar_mensaje("sbc/status/foto_lista", payload)

    else:
        print(f"[MQTT WARN] Tópico sin handler asignado: {topico}")


def arrancar_listener_global():
    """Conecta el escuchador y lo deja corriendo en bucle bloqueante"""
    cliente = mqtt.Client()
    cliente.on_message = _on_message
    
    try:
        cliente.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
        
        # Nos suscribimos a la raíz global para que al switch entre CUALQUIER cosa
        cliente.subscribe("sbc/notify", qos=1)
        print("[MQTT LISTENER] Escuchando todo el árbol 'sbc/notify' ")
        
        # loop_forever() se queda clavado ahí escuchando.
        # Ideal si este script va a ser un demonio/proceso que solo atiende la red.
        cliente.loop_forever()
        
    except Exception as e:
        print(f"[MQTT ERROR] Falló el listener global: {e}")