"""
Ejecutar Seelie localmente (sin Flask)
"""
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

import config
from database.models import db
from database.db_manager import db_manager
from handlers.messages import handle_group_message, handle_new_member
from handlers.commands import (
    cmd_warn, cmd_mute, cmd_unmute, cmd_ban,
    cmd_checkuser, cmd_history, cmd_trust, cmd_untrust,
    cmd_forgive, cmd_setrisk, cmd_config, cmd_modo,
    cmd_checkfotos, cmd_ayuda, cmd_pedidoincorrecto,
    cmd_auditoria, cmd_stats
)
from modules.scheduler import scheduler_module
from modules.requests import request_module
from modules.faq import get_faq_handlers, send_faq_dm
from modules.dm_handler import get_dm_handlers

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "Seelie - Sistema de Moderacion Activo\n\n"
        f"Modo: {config.MODE}\n"
        f"Modo prueba: {'SI' if config.TEST_MODE_ACTIVE else 'NO'}\n\n"
        "Usa /config para ver la configuracion completa."
    )

async def post_init(application):
    """Inicialización después de que se crea la aplicación"""
    # Inicializar base de datos si tiene el método
    if hasattr(db, 'init'):
        await db.init()
    scheduler_module.start(application)
    print(f"OK - Seelie inicializado correctamente")
    print(f"Modo: {config.MODE}")
    print(f"Modo prueba: {config.TEST_MODE_ACTIVE}")

def main():
    """Función principal"""
    print("\n" + "=" * 60)
    print("SEELIE - SISTEMA DE MODERACION (LOCAL)")
    print("=" * 60)
    print(f"\nModo: {config.MODE}")
    print(f"Modo prueba: {'ACTIVO' if config.TEST_MODE_ACTIVE else 'INACTIVO'}")
    print("\nInicializando...\n")
    
    # Crear aplicación
    application = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    # DM (mensajes privados al bot) - ANTES de /start genérico
    for handler in get_dm_handlers():
        application.add_handler(handler)
    
    # Comandos admin (inglés y español)
    application.add_handler(CommandHandler("start", start_command, filters=filters.ChatType.SUPERGROUP))
    
    # Moderación
    application.add_handler(CommandHandler("warn", cmd_warn))
    application.add_handler(CommandHandler("advertir", cmd_warn))
    
    application.add_handler(CommandHandler("mute", cmd_mute))
    application.add_handler(CommandHandler("silenciar", cmd_mute))
    
    application.add_handler(CommandHandler("unmute", cmd_unmute))
    application.add_handler(CommandHandler("desmutear", cmd_unmute))
    
    application.add_handler(CommandHandler("ban", cmd_ban))
    application.add_handler(CommandHandler("expulsar", cmd_ban))
    
    # Información
    application.add_handler(CommandHandler("checkuser", cmd_checkuser))
    application.add_handler(CommandHandler("verusuario", cmd_checkuser))
    
    application.add_handler(CommandHandler("history", cmd_history))
    application.add_handler(CommandHandler("historial", cmd_history))
    
    # Trusted
    application.add_handler(CommandHandler("trust", cmd_trust))
    application.add_handler(CommandHandler("confiar", cmd_trust))
    
    application.add_handler(CommandHandler("untrust", cmd_untrust))
    application.add_handler(CommandHandler("quitarconfianza", cmd_untrust))
    
    # Perdonar
    application.add_handler(CommandHandler("forgive", cmd_forgive))
    application.add_handler(CommandHandler("perdonar", cmd_forgive))
    
    # Riesgo y config
    application.add_handler(CommandHandler("setrisk", cmd_setrisk))
    application.add_handler(CommandHandler("config", cmd_config))
    application.add_handler(CommandHandler("ajustes", cmd_config))
    
    application.add_handler(CommandHandler("modo", cmd_modo))
    
    # Foto
    application.add_handler(CommandHandler("checkfotos", cmd_checkfotos))
    application.add_handler(CommandHandler("revisarfotos", cmd_checkfotos))
    
    # Ayuda
    application.add_handler(CommandHandler("ayuda", cmd_ayuda))
    
    # Pedido incorrecto
    application.add_handler(CommandHandler("pedidoincorrecto", cmd_pedidoincorrecto))
    
    # Auditoria
    application.add_handler(CommandHandler("auditoria", cmd_auditoria))
    print("OK - Handler /auditoria registrado")
    
    # Stats
    application.add_handler(CommandHandler("stats", cmd_stats))
    
    # FAQ
    for handler in get_faq_handlers():
        application.add_handler(handler)
    
    # Pedidos
    application.add_handler(CommandHandler("done", request_module.cmd_done))
    application.add_handler(CommandHandler("listo", request_module.cmd_done))
    
    application.add_handler(CommandHandler("solicitudes", request_module.cmd_pedidos))
    
    # Handler interactivo /pedido (ConversationHandler)
    application.add_handler(request_module.get_conversation_handler())
    
    # Handler de nuevos miembros
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_member
    ))
    
    # Handler de mensajes del grupo
    application.add_handler(MessageHandler(
        filters.ChatType.SUPERGROUP & ~filters.COMMAND,
        handle_group_message
    ))
    
    print("OK - Seelie esta corriendo localmente...")
    print("Presiona Ctrl+C para detener\n")
    
    # Ejecutar bot
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "edited_message", "channel_post",
                         "callback_query",
                         "my_chat_member", "chat_member", "chat_join_request"]
    )

if __name__ == '__main__':
    main()
