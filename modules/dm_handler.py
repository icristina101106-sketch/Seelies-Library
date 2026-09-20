"""
Módulo DM Handler - Manejo de mensajes privados al bot
Funciones: Menú principal, Contactar admin, Aportar libros, Reportar, Apelar, FAQ
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
import config


def _dm_menu_keyboard():
    """Teclado del menú principal del DM"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Preguntas Frecuentes", callback_data="dm_faq")],
        [InlineKeyboardButton("💬 Dudas / Contactar Admins", callback_data="dm_contacto")],
        [InlineKeyboardButton("📤 Aportar a la biblioteca", callback_data="dm_aportar")],
        [InlineKeyboardButton("🚨 Reportar usuario", callback_data="dm_reportar")],
        [InlineKeyboardButton("⚖️ Apelar castigo", callback_data="dm_apelar")],
    ])


def _cancel_keyboard():
    """Botón cancelar para flujos interactivos"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar", callback_data="dm_menu")]
    ])


async def dm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cuando alguien escribe /start o cualquier mensaje en DM"""
    # Protección contra duplicados - solo mostrar menú cada 3 segundos
    import time
    now = time.time()
    last_shown = context.user_data.get('last_menu_time', 0)
    if now - last_shown < 3:
        return  # Ignorar si se mostró hace menos de 3 segundos
    context.user_data['last_menu_time'] = now
    
    context.user_data.pop('dm_state', None)
    context.user_data.pop('aporte', None)
    context.user_data.pop('contacto', None)
    context.user_data.pop('reporte', None)
    context.user_data.pop('apelacion', None)
    
    keyboard = _dm_menu_keyboard()
    
    await update.message.reply_text(
        f"Hola **{update.effective_user.first_name}**\n\n"
        "Soy **Seelie**, el bot de la biblioteca.\n\n"
        "¿En qué te puedo ayudar?",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def dm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar clicks en botones del menú DM"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # --- Volver al menú principal ---
    if data == "dm_menu":
        # Protección contra duplicados
        import time
        now = time.time()
        last_shown = context.user_data.get('last_menu_time', 0)
        if now - last_shown < 2:
            return  # Ignorar clicks rápidos
        context.user_data['last_menu_time'] = now
        
        context.user_data.pop('dm_state', None)
        context.user_data.pop('aporte', None)
        context.user_data.pop('contacto', None)
        context.user_data.pop('reporte', None)
        context.user_data.pop('apelacion', None)
        keyboard = _dm_menu_keyboard()
        await query.edit_message_text(
            "¿En qué te puedo ayudar?",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # --- FAQ ---
    if data == "dm_faq":
        from modules.faq import _build_faq_keyboard
        keyboard = _build_faq_keyboard(page=0, dm_mode=True)
        await query.edit_message_text(
            "**Preguntas Frecuentes**\n\nSelecciona una pregunta:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # --- Contactar Admin ---
    if data == "dm_contacto":
        context.user_data['dm_state'] = 'contacto_tema'
        context.user_data['contacto'] = {}
        keyboard = _cancel_keyboard()
        await query.edit_message_text(
            "**Dudas / Contactar Administradoras**\n\n"
            "Si tienes una pregunta que no se responde en las Preguntas Frecuentes, o quieres contactar a la administración, te escucharán por aquí.\n\n"
            "Primero, ¿sobre qué **tema** es tu consulta?\n"
            "(Ej: duda sobre libros, sugerencia, problema con usuario, etc.)",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # --- Aportar a la biblioteca ---
    if data == "dm_aportar":
        context.user_data['dm_state'] = 'aporte_tipo'
        context.user_data['aporte'] = {}
        keyboard = _cancel_keyboard()
        await query.edit_message_text(
            "**Aportar a la biblioteca**\n\n"
            "Te guiaré paso a paso.\n\n"
            "¿Es una **saga, trilogía, duología** o **standalone** (autoconclusivo)?\n\n"
            "Opciones: `saga`, `trilogía`, `duología`, `standalone`",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # --- Saltar foto de portada (legacy) ---
    if data == "dm_aporte_skip_foto":
        await _send_aporte_to_admin(update, context, photos=[])
        return
    
    # --- Continuar a fotos ---
    if data == "dm_aporte_continue_foto":
        context.user_data['dm_state'] = 'aporte_fotos'
        await query.edit_message_text(
            "📸 Ahora envía las **fotos de portada** (una o varias).\n\n"
            "Cuando termines, toca \"Terminar\".",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Terminar aporte", callback_data="dm_aporte_finish")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="dm_menu")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # --- Terminar aporte ---
    if data == "dm_aporte_finish":
        photos = context.user_data.get('aporte', {}).get('photos', [])
        await _send_aporte_to_admin(update, context, photos=photos)
        return
    
    # --- Reportar usuario ---
    if data == "dm_reportar":
        context.user_data['dm_state'] = 'reportar_usuario'
        context.user_data['reporte'] = {}
        keyboard = _cancel_keyboard()
        await query.edit_message_text(
            "**Reportar usuario**\n\n"
            "Te guiaré paso a paso.\n\n"
            "¿Quién es el **usuario** que quieres reportar?\n"
            "(@username o nombre en el grupo)",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # --- Apelar castigo ---
    if data == "dm_apelar":
        context.user_data['dm_state'] = 'apelar_castigo'
        context.user_data['apelacion'] = {}
        keyboard = _cancel_keyboard()
        await query.edit_message_text(
            "**Apelar castigo**\n\n"
            "Te guiaré paso a paso.\n\n"
            "¿Qué **castigo** recibiste?\n"
            "(mute, ban, warning, etc.)",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return


async def dm_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto en DM según el estado"""
    state = context.user_data.get('dm_state')
    
    # --- Flujo de aporte interactivo ---
    if state == 'aporte_tipo':
        tipo = update.message.text.strip().lower()
        
        # Normalizar el tipo
        if tipo in ['trilogia', 'trilogía']:
            context.user_data['aporte']['tipo'] = 'trilogía'
            hint = "📖 Escribe los **3 títulos** separados por comas o saltos de línea:"
        elif tipo in ['duologia', 'duología', 'duo', 'dúo']:
            context.user_data['aporte']['tipo'] = 'duología'
            hint = "📖 Escribe los **2 títulos** separados por comas o saltos de línea:"
        elif tipo in ['saga']:
            context.user_data['aporte']['tipo'] = 'saga'
            hint = "📖 Escribe los **títulos de la saga** separados por comas o saltos de línea:"
        elif tipo in ['standalone', 'autoconclusivo', 'unico', 'único', 'no', 'n/a']:
            context.user_data['aporte']['tipo'] = 'standalone'
            hint = "📖 ¿Cuál es el **título** del libro?"
        else:
            # Por defecto tratar como standalone
            context.user_data['aporte']['tipo'] = 'standalone'
            hint = "📖 ¿Cuál es el **título** del libro?"
        
        context.user_data['dm_state'] = 'aporte_titulo'
        await update.message.reply_text(
            f"✅ Tipo: **{context.user_data['aporte']['tipo']}**\n\n{hint}",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'aporte_titulo':
        tipo = context.user_data['aporte'].get('tipo', 'standalone')
        titulos_texto = update.message.text.strip()
        
        # Guardar los títulos (puede ser uno o varios)
        context.user_data['aporte']['titulo'] = titulos_texto
        
        # Contar cuántos títulos parece haber
        import re
        titulos_lista = [t.strip() for t in re.split(r'[,\n]+', titulos_texto) if t.strip()]
        num_titulos = len(titulos_lista)
        
        # Mensaje de confirmación según el tipo
        if tipo == 'standalone':
            confirm = "✅ Título recibido"
        elif tipo == 'duología':
            confirm = f"✅ **Duología** - {num_titulos} títulos recibidos"
        elif tipo == 'trilogía':
            confirm = f"✅ **Trilogía** - {num_titulos} títulos recibidos"
        else:
            confirm = f"✅ **Saga** - {num_titulos} títulos recibidos"
        
        context.user_data['dm_state'] = 'aporte_autor'
        await update.message.reply_text(
            f"{confirm}\n\n¿Quién es el **autor**?",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'aporte_autor':
        context.user_data['aporte']['autor'] = update.message.text.strip()
        context.user_data['dm_state'] = 'aporte_idioma'
        await update.message.reply_text(
            "¿En qué **idioma** está?\n(Español / Inglés / Ambos)",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'aporte_idioma':
        context.user_data['aporte']['idioma'] = update.message.text.strip()
        context.user_data['dm_state'] = 'aporte_formato'
        await update.message.reply_text(
            "¿En qué **formato** es?\n(PDF / EPUB / Ambos)",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'aporte_formato':
        context.user_data['aporte']['formato'] = update.message.text.strip()
        context.user_data['dm_state'] = 'aporte_archivo'
        await update.message.reply_text(
            "Ahora envía el **archivo** del libro (PDF o EPUB).",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'aporte_archivo':
        await update.message.reply_text(
            "Necesito el **archivo** del libro (PDF o EPUB), no texto.\n"
            "Por favor envía el archivo.",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'aporte_foto':
        await update.message.reply_text(
            "Necesito una **foto de la portada** o toca \"Saltar\" si no tienes.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ Saltar (sin foto)", callback_data="dm_aporte_skip_foto")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="dm_menu")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # --- Flujo de CONTACTO interactivo ---
    if state == 'contacto_tema':
        context.user_data['contacto']['tema'] = update.message.text.strip()
        context.user_data['dm_state'] = 'contacto_mensaje'
        await update.message.reply_text(
            "Ahora escribe tu **pregunta o mensaje detallado**.\n\n"
            "Las administradoras lo leerán y te responderán pronto:",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'contacto_mensaje':
        context.user_data['contacto']['mensaje'] = update.message.text.strip()
        await _send_contacto_to_admin(update, context)
        return
    
    # --- Flujo de REPORTE interactivo ---
    if state == 'reportar_usuario':
        context.user_data['reporte']['usuario'] = update.message.text.strip()
        context.user_data['dm_state'] = 'reportar_problema'
        await update.message.reply_text(
            "¿Qué **hizo** esta persona? Describe el problema:",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'reportar_problema':
        context.user_data['reporte']['problema'] = update.message.text.strip()
        context.user_data['dm_state'] = 'reportar_evidencia'
        await update.message.reply_text(
            "¿Tienes **evidencia**? Envía una captura de pantalla, o escribe 'No':",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'reportar_evidencia':
        texto = update.message.text.strip().lower()
        if texto in ['no', 'nop', 'n', 'nope', 'skip', 'saltar']:
            await _send_reporte_to_admin(update, context, evidencia=None)
        else:
            # Guardar como evidencia de texto
            context.user_data['reporte']['evidencia_texto'] = update.message.text.strip()
            await _send_reporte_to_admin(update, context, evidencia=None)
        return
    
    # --- Flujo de APELACIÓN interactivo ---
    if state == 'apelar_castigo':
        context.user_data['apelacion']['castigo'] = update.message.text.strip()
        context.user_data['dm_state'] = 'apelar_fecha'
        await update.message.reply_text(
            "¿**Cuándo** ocurrió? (fecha aproximada, ejemplo: 'ayer', 'hace 3 días'):",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'apelar_fecha':
        context.user_data['apelacion']['fecha'] = update.message.text.strip()
        context.user_data['dm_state'] = 'apelar_explicacion'
        await update.message.reply_text(
            "¿Por qué crees que fue **injusto**? Explica tu situación:",
            reply_markup=_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    if state == 'apelar_explicacion':
        context.user_data['apelacion']['explicacion'] = update.message.text.strip()
        await _send_apelacion_to_admin(update, context)
        return
    
    # --- Flujos simples (fallback legacy) ---
    if state == 'contacto':
        await _forward_to_admin(update, context, tipo="contacto")
        return
    
    if state == 'reportar':
        await _forward_to_admin(update, context, tipo="reporte")
        return
    
    if state == 'apelar':
        await _forward_to_admin(update, context, tipo="apelacion")
        return
    
    # Sin estado → mostrar menú
    await dm_start(update, context)


async def dm_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar archivos enviados en DM"""
    state = context.user_data.get('dm_state')
    aporte = context.user_data.get('aporte', {})
    
    # Evitar procesar el mismo archivo dos veces
    file_unique_id = update.message.document.file_unique_id if update.message.document else None
    if file_unique_id and aporte.get('last_file_id') == file_unique_id:
        return  # Ya procesamos este archivo
    
    # Archivo del aporte - aceptar múltiples archivos
    if state in ['aporte_archivo', 'aporte_archivos']:
        # Inicializar lista si es el primer archivo
        if 'files' not in context.user_data['aporte']:
            context.user_data['aporte']['files'] = []
            context.user_data['dm_state'] = 'aporte_archivos'  # Estado de múltiples archivos
        
        # Evitar duplicados
        if file_unique_id and file_unique_id in [f.get('file_unique_id') for f in context.user_data['aporte']['files']]:
            return
        
        # Guardar archivo
        context.user_data['aporte']['files'].append({
            'file_id': update.message.document.file_id,
            'file_name': update.message.document.file_name or "archivo",
            'file_unique_id': file_unique_id
        })
        
        num_files = len(context.user_data['aporte']['files'])
        await update.message.reply_text(
            f"✅ Archivo {num_files} guardado: `{update.message.document.file_name}`\n\n"
            "📎 Envía más archivos si tienes, o toca \"Continuar\" para pasar a las fotos.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➡️ Continuar (a fotos)", callback_data="dm_aporte_continue_foto")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="dm_menu")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # Evidencia de reporte (archivo/documento)
    if state == 'reportar_evidencia':
        # Guardar ID del documento y enviar reporte
        context.user_data['reporte']['evidencia_doc'] = {
            'file_id': update.message.document.file_id,
            'file_name': update.message.document.file_name or "evidencia"
        }
        await _send_reporte_to_admin(update, context, evidencia='doc')
        return
    
    # Otros estados que aceptan archivos
    if state == 'contacto':
        await _forward_to_admin(update, context, tipo="contacto")
        return
    
    if state == 'reportar':
        await _forward_to_admin(update, context, tipo="reporte")
        return
    
    if state == 'apelar':
        await _forward_to_admin(update, context, tipo="apelacion")
        return
    
    # Sin estado → mostrar menú
    await dm_start(update, context)


async def dm_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar fotos enviadas en DM"""
    state = context.user_data.get('dm_state')
    
    # Evidencia de reporte (foto)
    if state == 'reportar_evidencia':
        photo_id = update.message.photo[-1].file_id
        await _send_reporte_to_admin(update, context, evidencia=photo_id)
        return
    
    # Foto de portada del aporte - aceptar múltiples fotos
    if state in ['aporte_foto', 'aporte_fotos']:
        photo_id = update.message.photo[-1].file_id
        file_unique_id = update.message.photo[-1].file_unique_id
        
        # Inicializar lista si es la primera foto
        if 'photos' not in context.user_data['aporte']:
            context.user_data['aporte']['photos'] = []
            context.user_data['dm_state'] = 'aporte_fotos'
        
        # Evitar duplicados
        if file_unique_id in [p.get('file_unique_id') for p in context.user_data['aporte']['photos']]:
            return
        
        context.user_data['aporte']['photos'].append({
            'file_id': photo_id,
            'file_unique_id': file_unique_id
        })
        
        num_photos = len(context.user_data['aporte']['photos'])
        await update.message.reply_text(
            f"📸 Foto {num_photos} guardada.\n\n"
            "Envía más fotos si tienes, o toca \"Terminar\".",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Terminar aporte", callback_data="dm_aporte_finish")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="dm_menu")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # Otros estados que aceptan fotos
    if state == 'contacto':
        await _forward_to_admin(update, context, tipo="contacto")
        return
    
    if state == 'reportar':
        await _forward_to_admin(update, context, tipo="reporte")
        return
    
    if state == 'apelar':
        await _forward_to_admin(update, context, tipo="apelacion")
        return
    
    # Sin estado → mostrar menú
    await dm_start(update, context)


async def _send_aporte_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, photos=None):
    """Enviar aporte completo al admin"""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    aporte = context.user_data.get('aporte', {})
    tipo = aporte.get('tipo', 'standalone')
    photos = photos or []
    
    # Formatear título según tipo
    if tipo == 'standalone':
        titulo_label = "Título"
    elif tipo == 'duología':
        titulo_label = "Títulos (Duología)"
    elif tipo == 'trilogía':
        titulo_label = "Títulos (Trilogía)"
    else:
        titulo_label = "Títulos (Saga)"
    
    # Formatear múltiples títulos con numeración
    import re
    titulos_lista = [t.strip() for t in re.split(r'[,\n]+', aporte.get('titulo', '?')) if t.strip()]
    if len(titulos_lista) > 1:
        titulo_formateado = '\n'.join([f"   {i+1}. {t}" for i, t in enumerate(titulos_lista)])
    else:
        titulo_formateado = aporte.get('titulo', '?')
    
    # Contar archivos
    files = aporte.get('files', [])
    num_files = len(files)
    
    header = (
        f"📤 **APORTE A LA BIBLIOTECA**\n"
        f"{'=' * 30}\n"
        f"De: {username} (ID: {user.id})\n"
        f"{'=' * 30}\n\n"
        f"**{titulo_label}:**\n{titulo_formateado}\n\n"
        f"**Autor:** {aporte.get('autor', '?')}\n"
        f"**Idioma:** {aporte.get('idioma', '?')}\n"
        f"**Formato:** {aporte.get('formato', '?')}\n"
        f"**Archivos:** {num_files}"
    )
    
    # Enviar info al admin
    await context.bot.send_message(
        chat_id=config.ALERT_GROUP_ID,
        message_thread_id=config.ALERT_TOPIC_ID,
        text=header,
        parse_mode='Markdown'
    )
    
    # Enviar todos los archivos
    for i, f in enumerate(files, 1):
        await context.bot.send_document(
            chat_id=config.ALERT_GROUP_ID,
            message_thread_id=config.ALERT_TOPIC_ID,
            document=f['file_id'],
            caption=f"Archivo {i}/{num_files}: {f['file_name']}"
        )
    
    # Enviar todas las fotos
    for i, p in enumerate(photos, 1):
        await context.bot.send_photo(
            chat_id=config.ALERT_GROUP_ID,
            message_thread_id=config.ALERT_TOPIC_ID,
            photo=p['file_id'],
            caption=f"Portada {i}/{len(photos)}" if len(photos) > 1 else "Foto de portada"
        )
    
    # Confirmar al usuario
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al menú", callback_data="dm_menu")],
    ])
    
    # Determinar si viene de callback (skip foto) o de mensaje
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Tu aporte fue recibido.\n"
            "Un admin lo revisará y si es aprobado, se publicará en la biblioteca.\n\n"
            "¿Algo más?",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "Tu aporte fue recibido.\n"
            "Un admin lo revisará y si es aprobado, se publicará en la biblioteca.\n\n"
            "¿Algo más?",
            reply_markup=keyboard
        )
    
    # Limpiar estado
    context.user_data.pop('dm_state', None)
    context.user_data.pop('aporte', None)


async def _forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, tipo: str):
    """Reenviar mensaje del usuario al canal de alertas del admin"""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    
    headers = {
        "contacto": "💬 **MENSAJE DE USUARIO**",
        "reporte": "🚨 **REPORTE DE USUARIO**",
        "apelacion": "⚖️ **APELACIÓN DE CASTIGO**",
    }
    
    header = (
        f"{headers.get(tipo, '📩 **MENSAJE**')}\n"
        f"{'=' * 30}\n"
        f"De: {username} (ID: {user.id})\n"
        f"{'=' * 30}\n\n"
    )
    
    # Enviar header al admin
    await context.bot.send_message(
        chat_id=config.ALERT_GROUP_ID,
        message_thread_id=config.ALERT_TOPIC_ID,
        text=header,
        parse_mode='Markdown'
    )
    
    # Reenviar el mensaje original
    await update.message.forward(
        chat_id=config.ALERT_GROUP_ID,
        message_thread_id=config.ALERT_TOPIC_ID
    )
    
    # Confirmar al usuario
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al menú", callback_data="dm_menu")],
    ])
    
    confirmations = {
        "contacto": "Tu mensaje fue enviado a las administradoras.\nTe responderán cuando lo vean.",
        "reporte": "Tu reporte fue recibido.\nLas administradoras lo revisarán lo antes posible.",
        "apelacion": "Tu apelación fue recibida.\nLas administradoras revisarán tu caso.",
    }
    
    await update.message.reply_text(
        f"{confirmations.get(tipo, 'Recibido.')}\n\n¿Algo más?",
        reply_markup=keyboard
    )
    
    # Limpiar estado
    context.user_data.pop('dm_state', None)


async def _send_contacto_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enviar contacto completo al admin"""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    contacto = context.user_data.get('contacto', {})
    
    header = (
        f"💬 **MENSAJE DE USUARIO**\n"
        f"{'=' * 30}\n"
        f"De: {username} (ID: {user.id})\n"
        f"{'=' * 30}\n\n"
        f"**Tema:** {contacto.get('tema', '?')}\n\n"
        f"**Mensaje:**\n{contacto.get('mensaje', '?')}"
    )
    
    # Enviar al admin
    await context.bot.send_message(
        chat_id=config.ALERT_GROUP_ID,
        message_thread_id=config.ALERT_TOPIC_ID,
        text=header,
        parse_mode='Markdown'
    )
    
    # Confirmar al usuario
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al menú", callback_data="dm_menu")],
    ])
    
    await update.message.reply_text(
        "Tu pregunta o mensaje fue enviado a las administradoras.\n"
        "Te responderán por aquí en cuanto puedan revisarlo.\n\n"
        "¿Puedo ayudarte con algo más?",
        reply_markup=keyboard
    )
    
    # Limpiar estado
    context.user_data.pop('dm_state', None)
    context.user_data.pop('contacto', None)


async def _send_reporte_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, evidencia=None):
    """Enviar reporte completo al admin"""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    reporte = context.user_data.get('reporte', {})
    
    header = (
        f"🚨 **REPORTE DE USUARIO**\n"
        f"{'=' * 30}\n"
        f"De: {username} (ID: {user.id})\n"
        f"{'=' * 30}\n\n"
        f"**Usuario reportado:** {reporte.get('usuario', '?')}\n\n"
        f"**Problema:**\n{reporte.get('problema', '?')}"
    )
    
    if reporte.get('evidencia_texto'):
        header += f"\n\n**Evidencia (texto):**\n{reporte['evidencia_texto']}"
    
    # Enviar al admin
    await context.bot.send_message(
        chat_id=config.ALERT_GROUP_ID,
        message_thread_id=config.ALERT_TOPIC_ID,
        text=header,
        parse_mode='Markdown'
    )
    
    # Enviar evidencia si es foto o documento
    if evidencia == 'doc' and reporte.get('evidencia_doc'):
        await context.bot.send_document(
            chat_id=config.ALERT_GROUP_ID,
            message_thread_id=config.ALERT_TOPIC_ID,
            document=reporte['evidencia_doc']['file_id'],
            caption="Evidencia del reporte"
        )
    elif evidencia:
        await context.bot.send_photo(
            chat_id=config.ALERT_GROUP_ID,
            message_thread_id=config.ALERT_TOPIC_ID,
            photo=evidencia,
            caption="Evidencia del reporte"
        )
    
    # Confirmar al usuario
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al menú", callback_data="dm_menu")],
    ])
    
    await update.message.reply_text(
        "Tu reporte fue recibido.\n"
        "Las administradoras lo revisarán lo antes posible.\n\n"
        "¿Algo más?",
        reply_markup=keyboard
    )
    
    # Limpiar estado
    context.user_data.pop('dm_state', None)
    context.user_data.pop('reporte', None)


async def _send_apelacion_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enviar apelación completa al admin"""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    apelacion = context.user_data.get('apelacion', {})
    
    header = (
        f"⚖️ **APELACIÓN DE CASTIGO**\n"
        f"{'=' * 30}\n"
        f"De: {username} (ID: {user.id})\n"
        f"{'=' * 30}\n\n"
        f"**Castigo:** {apelacion.get('castigo', '?')}\n"
        f"**Cuándo:** {apelacion.get('fecha', '?')}\n\n"
        f"**Explicación:**\n{apelacion.get('explicacion', '?')}"
    )
    
    # Registrar la apelación en BD
    appeal_id = await db_manager.save_appeal(
        user_id=user.id,
        appeal_type=apelacion.get('castigo', 'desconocido'),
        reason=apelacion.get('explicacion', '?'),
        conversation=str(apelacion)
    )
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Aprobar (Perdonar)", callback_data=f"appeal_approve|{appeal_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"appeal_reject|{appeal_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Enviar al admin
    await context.bot.send_message(
        chat_id=config.ALERT_GROUP_ID,
        message_thread_id=config.ALERT_TOPIC_ID,
        text=header,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    # Confirmar al usuario
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al menú", callback_data="dm_menu")],
    ])
    
    await update.message.reply_text(
        "Tu apelación fue recibida.\n"
        "Las administradoras revisarán tu caso.\n\n"
        "¿Algo más?",
        reply_markup=keyboard
    )
    
    # Limpiar estado
    context.user_data.pop('dm_state', None)
    context.user_data.pop('apelacion', None)


def get_dm_handlers():
    """Devolver los handlers para mensajes privados"""
    return [
        # /start en DM
        CommandHandler("start", dm_start, filters=filters.ChatType.PRIVATE),
        # Callbacks de botones DM
        CallbackQueryHandler(dm_callback, pattern=r"^dm_"),
        # Mensajes de texto en DM
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            dm_message
        ),
        # Archivos en DM
        MessageHandler(
            filters.ChatType.PRIVATE & filters.Document.ALL,
            dm_document
        ),
        # Fotos en DM
        MessageHandler(
            filters.ChatType.PRIVATE & filters.PHOTO,
            dm_photo
        ),
    ]
