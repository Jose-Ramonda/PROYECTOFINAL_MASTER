#   Módulo de Procesamiento de Callbacks de comandos
#   Autor: José Ramonda
#   Ultima modificación 11/7/2026

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from . import menu
from . import auth
from . import MQTT

# Volvemos a importar los números de estado para poder mover la máquina desde acá
# Usamos un truco para no re-declarar todo: los importamos de estados directamente más tarde o los hardcodeamos.
# Para mantener el desacople, sabemos que EN_MENU_USUARIO es 2 y ESPERANDO_CLAVE_ADMIN es 3.
ESPERANDO_CLAVE_ADMIN = 3
EN_MENU_USUARIO = 2

async def procesar_botones_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interpreta los clicks del menú de usuario estándar y sus submenús"""
    query = update.callback_query
    await query.answer() 

    # El usuario pide ver el submenú de puertas

    if query.data == "usr_abrir_menu":
        await query.edit_message_text( # <-- EDITAMOS el mensaje en vez de responder uno nuevo
            text="Seleccione que acceso desea abrir:",
            reply_markup=menu.submenu_nodos("abrir")
        )
        return EN_MENU_USUARIO

    # El usuario pide ver el submenú de cámaras
    elif query.data == "usr_foto_menu":
        await query.edit_message_text( # <-- EDITAMOS
            text="Seleccione de que acceso desea tomar fotografia:",
            reply_markup=menu.submenu_nodos("foto")
        )
        return EN_MENU_USUARIO


    # El botón "Atrás" de los submenús: redibuja el menú raíz de usuario
    elif query.data == "usr_volver_raiz":
        await query.message.reply_text(
            text="Menu Principal:",
            reply_markup=menu.menu_usuario()
        )
        return EN_MENU_USUARIO

    # 4. Solicitud de escalado de privilegios
    elif query.data == "usr_ir_admin":
        await query.message.reply_text("Modo Administrador solicitado. Ingrese la clave de privilegios:")
        return ESPERANDO_CLAVE_ADMIN
        
    elif query.data == "usr_progmode":
        await query.message.reply_text(
            text="Modo programacion seleccionado (Función en desarrollo).", 
            reply_markup=menu.menu_usuario()
        )
        return EN_MENU_USUARIO

    return EN_MENU_USUARIO


async def procesar_botones_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interpreta los clicks del menú de administración avanzada"""
    query = update.callback_query
    await query.answer()

    # Opción A: Listar usuarios (Auditoría)
    if query.data == "adm_listar":
        # Llamamos a tu función de auth.py que lee el JSON
        reporte = auth.obtener_informe_usuarios()
        
        texto_informe = "**INFORME ACTUAL DE USUARIOS:**\n\n"
        for usuario, privilegio in reporte.items():
            texto_informe += f"`{usuario:<10}` : {privilegio}\n"
            
        await query.message.reply_text(text=texto_informe, parse_mode="Markdown")
        return EN_MENU_USUARIO # Nos quedamos en el entorno de menús

    # Opción B: Modificar credenciales (Por ahora un cartel estático escalable)
    elif query.data == "adm_modificar":
        # TODO: Acá en el futuro moveremos a un estado 'ESPERANDO_EDICION' 
        # para que el admin tipee "Daniel clavenueva" y se guarde en el JSON.
        await query.message.reply_text("Función de edición en desarrollo. Próximamente se podrá modificar el JSON desde acá.")
        return EN_MENU_USUARIO

    # Opción C: Salir del modo administrador de forma segura
    elif query.data == "adm_volver_usr":
        context.user_data["rol"] = "USUARIO" # Bajamos el privilegio en RAM
        await query.message.reply_text(
            text="Saliendo de Modo Admin. Volviendo a interfaz estándar:",
            reply_markup=menu.menu_usuario() # Le redibujamos el teclado común
        )
        return EN_MENU_USUARIO

    return EN_MENU_USUARIO


async def procesar_comandos_hardware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ataja el click de selección final del submenú (ej: cmd_abrir_0x0A) y gatilla MQTT"""
    query = update.callback_query
    await query.answer()
    
    orden = query.data  # "cmd_abrir_0x0A"
    partes = orden.split("_")
    accion = partes[1]  # "abrir" o "foto"
    nodo = partes[2]    # "0x0A"

    chat_id = query.message.chat_id
    payload_extendido = f"{nodo},{chat_id}" # "0x0A,8816825051"

    # 1. Forzamos la publicación del payload COMPLETO
    exito = MQTT.publicar_comando(accion, payload_extendido)
    
    if exito:
        mensaje = f"Orden enviada para {accion.upper()} en nodo {nodo}.\nEsperando respuesta del hardware..."
    else:
        mensaje = f"Error crítico: No se pudo conectar con el broker MQTT."
        
    # 2. EN VEZ DE REPLY_TEXT, EDITAMOS EL MENSAJE ACTUAL 
    # Esto borra el submenú viejo y estampa el menú principal limpio.
    await query.edit_message_text(
        text=f"{mensaje}\n\nMenú Principal:",
        reply_markup=menu.menu_usuario()
    )
    
    # 3. Retornamos el estado correcto para que la MEF sepa dónde quedó parada
    return EN_MENU_USUARIO