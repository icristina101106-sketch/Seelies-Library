"""
Módulo FAQ - Preguntas frecuentes con botones interactivos
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import config

# ===== PREGUNTAS Y RESPUESTAS =====
FAQ_DATA = [
    {
        "id": "pedir_libro",
        "button": "📖 ¿Cómo pido un libro?",
        "answer": (
            "**¿Cómo pido un libro?**\n\n"
            "Usa el comando /pedido en el tema de **Peticiones** y el bot te guiará paso a paso.\n\n"
            "**IMPORTANTE:** Antes de pedir, usa la lupa y busca en los archivos del grupo. Es muy probable que ya esté.\n\n"
            "Los **Viernes y Domingos** los pedidos están **cerrados** (días de descanso para las admins)."
        )
    },
    {
        "id": "formato_pedido",
        "button": "📝 ¿Cuál es el formato para pedir?",
        "answer": (
            "**¿Cuál es el formato para pedir un libro?**\n\n"
            "Al usar /pedido, el bot te pide 4 datos:\n"
            "- **Título** — Nombre completo del libro\n"
            "- **Autor** — Nombre del autor\n"
            "- **Idioma** — Español, Inglés o Ambos\n"
            "- **Formato** — PDF, EPUB o Ambos\n\n"
            "**Para sagas/trilogías:** Especifica el nombre de la saga y la lista de libros que la componen.\n\n"
            "**Libros de Wattpad:** Indícalo en tu pedido. Solo se buscan si la novela está COMPLETA."
        )
    },
    {
        "id": "reglas",
        "button": "📜 Reglas del grupo",
        "answer": (
            "**Reglas del grupo**\n\n"
            "1. **Busca antes de pedir** — Usa la lupa en archivos\n"
            "2. **Usa /pedido** para pedir libros con el formato correcto\n"
            "3. **No spam, no links externos, no vender libros**\n"
            "4. **No contenido +18, gore ni discursos de odio**\n"
            "5. **Foto de perfil obligatoria**\n"
            "6. **Al reenviar archivos:** usa \"Ocultar Remitente\"\n"
            "7. **Viernes y Domingos** pedidos cerrados\n"
            "8. **Respeto y amabilidad** — Las admins son voluntarias\n\n"
            "El incumplimiento resulta en expulsión sin aviso."
        )
    },
    {
        "id": "tiempo_pedido",
        "button": "⏰ ¿Cuánto tardan mi pedido?",
        "answer": (
            "**¿Cuánto tardan en atender mi pedido?**\n\n"
            "El tiempo varía según el libro. Puedes ver el estado por las reacciones:\n\n"
            "🍓 = Pedido listo / Entregado\n"
            "👀 = Buscando\n"
            "👎 = Libro NO encontrado\n"
            "❌ = Pedido eliminado por mal formato (debes rehacerlo)\n\n"
            "📅 **Viernes y Domingos** no se atienden pedidos.\n"
            "💡 Libros recién publicados probablemente no están en digital aún. ¡Paciencia!"
        )
    },
    {
        "id": "buscar_biblioteca",
        "button": "🔍 ¿Cómo busco en la biblioteca?",
        "answer": (
            "**¿Cómo busco un libro en la biblioteca?**\n\n"
            "1. Entra al tema **Biblioteca ESP** o **Biblioteca ENG**\n"
            "2. Usa la lupa de Telegram\n"
            "3. Busca en \"Archivos\" o \"Multimedia\"\n"
            "4. Escribe el título o autor\n\n"
            "**Siempre busca antes de pedir.** Es la regla #1 del grupo."
        )
    },
    {
        "id": "libros_ingles",
        "button": "🌐 ¿Puedo pedir en inglés?",
        "answer": (
            "**¿Puedo pedir libros en inglés?**\n\n"
            "Sí. Tenemos biblioteca en ambos idiomas:\n"
            "- **Biblioteca ESP** — Español\n"
            "- **Biblioteca ENG** — Inglés\n\n"
            "Al hacer tu /pedido, elige \"Inglés\" o \"Ambos\" cuando el bot pregunte el idioma."
        )
    },
    {
        "id": "foto_perfil",
        "button": "📷 ¿Por qué me piden foto?",
        "answer": (
            "**¿Por qué me piden foto de perfil?**\n\n"
            "Es una medida de seguridad para el grupo. Nos ayuda a garantizar que los miembros son personas reales y no bots o cuentas falsas.\n\n"
            "Al entrar tienes **24 horas** para poner una foto de perfil pública.\n"
            "Recibirás un recordatorio a las **12 horas**.\n"
            "La foto debe ser una imagen real, no un símbolo o letra.\n"
            "Si no cumples, serás removido del grupo.\n\n"
            "Puedes volver a entrar una vez que tengas foto. Es por la seguridad de todos."
        )
    },
    {
        "id": "mensaje_borrado",
        "button": "🚫 ¿Por qué se borró mi mensaje?",
        "answer": (
            "**¿Por qué se borró mi mensaje?**\n\n"
            "El bot elimina automáticamente mensajes que contengan:\n\n"
            "- Links externos o invitaciones a otros grupos\n"
            "- Spam o mensajes repetidos\n"
            "- Flood (muchos mensajes muy rápido)\n"
            "- Archivos sospechosos (.exe, .apk, etc.)\n"
            "- Palabras prohibidas\n\n"
            "Si crees que fue un error, contacta a un admin."
        )
    },
    {
        "id": "contactar_admin",
        "button": "❓ ¿Cómo contacto a un admin?",
        "answer": (
            "**¿Cómo contacto a un admin?**\n\n"
            "Puedes escribirle al bot **Seelie** y tu mensaje llegará automáticamente.\n\n"
            "También puedes escribir en el tema de **General** mencionando tu duda.\n"
            "Enviar mensaje privado a las admins no está prohibido, pero es raro que contesten por ahí."
        )
    },
    {
        "id": "descargar",
        "button": "📱 ¿Cómo descargo los libros?",
        "answer": (
            "**¿Cómo descargo los libros?**\n\n"
            "Los libros se comparten como archivos en Telegram.\n\n"
            "El tutorial completo para descargar archivos en un grupo donde está restringido lo encuentras en el tema **Tutoriales**."
        )
    },
    {
        "id": "pedido_duplicado",
        "button": "🔄 ¿Puedo pedir algo ya pedido?",
        "answer": (
            "**¿Puedo pedir un libro que ya pidió alguien más?**\n\n"
            "Antes de pedir, revisa si el libro ya está en la biblioteca:\n"
            "1. Busca en **Biblioteca ESP** o **Biblioteca ENG**\n"
            "2. Revisa los pedidos pendientes en **Peticiones**\n\n"
            "Si ya fue pedido y está pendiente, no hace falta pedirlo de nuevo.\n"
            "Si ya fue subido, búscalo en la biblioteca."
        )
    },
    {
        "id": "compartir_libros",
        "button": "📤 ¿Puedo compartir libros?",
        "answer": (
            "**¿Puedo compartir libros?**\n\n"
            "No se puede compartir archivos directamente en el grupo. Consideramos que es peligroso dar permiso de mandar archivos, ya que pueden romper las reglas.\n\n"
            "Si quieres hacer un aporte, mándalo al **DM del bot Seelie** y será revisado por un admin. Al ser aprobado, se publicará en la biblioteca."
        )
    },
    {
        "id": "contenido_prohibido",
        "button": "🚫 ¿Qué NO se puede compartir?",
        "answer": (
            "**¿Qué tipo de contenido NO se puede compartir?**\n\n"
            "Está prohibido compartir:\n\n"
            "- Links externos o invitaciones a otros grupos/canales\n"
            "- Spam o publicidad\n"
            "- Contenido +18, gore o discursos de odio\n"
            "- Archivos ejecutables (.exe, .apk)\n"
            "- Venta de libros o cualquier contenido\n\n"
            "Solo la administración puede compartir enlaces. El incumplimiento resulta en expulsión."
        )
    },
    {
        "id": "libro_listo",
        "button": "🔔 ¿Cómo sé si mi libro está listo?",
        "answer": (
            "**¿Cómo sé cuando mi libro está listo?**\n\n"
            "Las admins usan reacciones para indicar el estado:\n\n"
            "🍓 = Pedido listo / Entregado\n"
            "👀 = Buscando\n"
            "👎 = Libro NO encontrado\n"
            "❌ = Pedido eliminado por mal formato\n\n"
            "Cuando esté listo, busca el libro en la **Biblioteca** correspondiente."
        )
    },
    {
        "id": "varios_pedidos",
        "button": "📚 ¿Puedo pedir más de uno?",
        "answer": (
            "**¿Puedo pedir más de un libro a la vez?**\n\n"
            "Sí, pero con moderación.\n\n"
            "Haz un /pedido a la vez.\n"
            "Espera a que termines uno antes de iniciar otro.\n"
            "No hagas demasiados pedidos seguidos.\n\n"
            "Las admins atienden voluntariamente. Sé paciente."
        )
    },
    {
        "id": "pedido_desaparecio",
        "button": "🗑️ ¿Por qué desapareció mi pedido?",
        "answer": (
            "**¿Por qué desapareció mi pedido?**\n\n"
            "Los pedidos se eliminan automáticamente **24 horas después de ser atendidos**.\n"
            "Esto mantiene el tema de Peticiones limpio y organizado.\n\n"
            "Si tu pedido desapareció sin ser atendido, contacta a un admin."
        )
    },
]

# Dividir en páginas de 9 botones (para no saturar)
FAQ_PAGE_SIZE = 8


async def cmd_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /faq - Mostrar preguntas frecuentes con botones"""
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id
    
    # Borrar comando
    try:
        await update.message.delete()
    except:
        pass
    
    keyboard = _build_faq_keyboard(page=0)
    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text="📚 **PREGUNTAS FRECUENTES**\n\nSelecciona una pregunta:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar clicks en botones del FAQ"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    is_dm = query.message.chat.type == 'private'
    
    # Navegación de páginas
    if data.startswith("faq_page_"):
        page = int(data.split("_")[-1])
        keyboard = _build_faq_keyboard(page=page, dm_mode=is_dm)
        await query.edit_message_text(
            text="**Preguntas Frecuentes**\n\nSelecciona una pregunta:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # Botón "Volver"
    if data == "faq_back":
        keyboard = _build_faq_keyboard(page=0, dm_mode=is_dm)
        await query.edit_message_text(
            text="**Preguntas Frecuentes**\n\nSelecciona una pregunta:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # Mostrar respuesta
    if data.startswith("faq_"):
        faq_id = data[4:]  # quitar "faq_"
        for item in FAQ_DATA:
            if item["id"] == faq_id:
                buttons = [[InlineKeyboardButton("⬅️ Volver a preguntas", callback_data="faq_back")]]
                if is_dm:
                    buttons.append([InlineKeyboardButton("🏠 Menú principal", callback_data="dm_menu")])
                keyboard = InlineKeyboardMarkup(buttons)
                await query.edit_message_text(
                    text=item["answer"],
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return


async def send_faq_dm(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Enviar FAQ por mensaje privado a un nuevo miembro"""
    welcome_faq = (
        f"👋 **¡Bienvenid@ a {config.GROUP_NAME}!**\n\n"
        "Me llamo Selene, y soy la asistente del grupo. Aquí tienes información útil para empezar:\n\n"
        "🌟 **Los 3 ERRORES MÁS COMUNES (¡Evítalos!)**\n"
        "1️⃣ **Pedir un libro sin formato:** No pidas libros como texto normal. Siempre usa el comando `/pedido` en el tema de Peticiones.\n"
        "2️⃣ **Subir spam/links externos:** Está estrictamente prohibido, puedes ser baneado automáticamente.\n"
        "3️⃣ **No usar el buscador:** Antes de pedir, ¡asegúrate de buscar si el libro ya está! Usa `/buscar título`.\n\n"
        "⚙️ **OTRAS REGLAS**\n"
        "📸 **Foto de perfil:** Tienes 24h para poner una foto pública (obligatorio).\n\n"
        "📖 Usa `/faq` en el grupo para ver todas las preguntas frecuentes.\n\n"
        "¡Disfruta tu estancia y feliz lectura! 🦋📚"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=welcome_faq,
            parse_mode='Markdown'
        )
        return True
    except Exception:
        # El usuario no ha iniciado chat con el bot (común)
        return False


def _build_faq_keyboard(page=0, dm_mode=False):
    """Construir teclado inline con botones de FAQ paginados"""
    start = page * FAQ_PAGE_SIZE
    end = start + FAQ_PAGE_SIZE
    page_items = FAQ_DATA[start:end]
    
    keyboard = []
    for item in page_items:
        keyboard.append([
            InlineKeyboardButton(item["button"], callback_data=f"faq_{item['id']}")
        ])
    
    # Botones de navegación
    nav_buttons = []
    total_pages = (len(FAQ_DATA) + FAQ_PAGE_SIZE - 1) // FAQ_PAGE_SIZE
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"faq_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"faq_page_{page + 1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # En DM, agregar botón para volver al menú principal
    if dm_mode:
        keyboard.append([InlineKeyboardButton("🏠 Menú principal", callback_data="dm_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_faq_handlers():
    """Devolver los handlers necesarios para el FAQ"""
    return [
        CommandHandler(["faq", "preguntasfrecuentes"], cmd_faq),
        CallbackQueryHandler(faq_callback, pattern=r"^faq_"),
    ]
