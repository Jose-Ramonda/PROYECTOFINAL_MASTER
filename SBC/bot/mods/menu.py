#   Módulo de Diseño de Menús Interactivos
#   Autor: José Ramonda
#   Modificado 11/7/2026

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import botconfig

def menu_usuario():
    """Genera el teclado interactivo para el rol de Usuario Común"""
    # Cada lista interna representa una fila de botones en la pantalla del celular
    botones = [
        [
            InlineKeyboardButton("Abrir puerta", callback_data="usr_abrir_menu"),
        ],
        [
            InlineKeyboardButton("Tomar fotografía", callback_data="usr_foto_menu")
        ],
        [
            InlineKeyboardButton("Modo Administrador", callback_data="usr_ir_admin"),
            InlineKeyboardButton("Modo programación", callback_data="usr_progmode")
        ]
    ]
    return InlineKeyboardMarkup(botones)

def menu_administrador():
    """Genera el teclado interactivo para el rol de Administrador"""
    botones = [
        [
            InlineKeyboardButton("Listar Usuarios", callback_data="adm_listar"),
            InlineKeyboardButton("Modificar Credenciales", callback_data="adm_modificar")
        ],
        [
            # Permite al admin volver a la interfaz de usuario normal
            InlineKeyboardButton("<- Volver", callback_data="adm_volver_usr")
        ]
    ]
    return InlineKeyboardMarkup(botones)

def submenu_nodos(accion):
    """
    Genera el menú de selección de hardware dinámicamente 
    leyendo las IDs reales del bus desde botconfig.
    """
    botones = []
    
    # Recorremos el diccionario: id_hex es "0x0A", nombre es "Acceso Frente"
    for id_hex, nombre in botconfig.DICCIONARIO_NODOS.items():
        # Creamos una fila por cada nodo con su ID real embebida en el callback
        fila = [InlineKeyboardButton(nombre, callback_data=f"cmd_{accion}_{id_hex}")]
        botones.append(fila)
        
    # Al final, le agregamos el botón de volver al menú raíz
    # Ojo: como este submenu lo abren los usuarios, tiene que volver al menú raíz de usuario
    botones.append([InlineKeyboardButton("<- Volver", callback_data="usr_volver_raiz")])
    
    return InlineKeyboardMarkup(botones)