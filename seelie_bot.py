"""
SEELIE - Sistema de Moderación y Administración para Telegram
Bot inteligente con moderación automática, gestión de usuarios y biblioteca

Fase 1: Núcleo del sistema
- Moderación automática
- Sistema de warnings y riesgo
- Gestión de usuarios y estados
- Comandos admin
- Backup de biblioteca
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
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
    cmd_forgive, cmd_setrisk, cmd_config, cmd_modo
)
from modules.scheduler import scheduler_module
from modules.requests import request_module

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "Seelie - Sistema de Moderacion Activo\n\n"
        f"Modo: {config.MODE}\n"
        f"Modo prueba: {'SI' if config.TEST_MODE_ACTIVE else 'NO'}\n\n"
        "Usa /config para ver la configuracion completa."
    )

async def post_init(application):
    """Inicialización después de crear la aplicación"""
    # Inicializar base de datos
    await db.init_database()
    await db.populate_forbidden_words()
    
    # Iniciar scheduler
    scheduler_module.start(application.bot)
    
    logger.info("OK - Seelie inicializado correctamente")
    logger.info(f"Modo: {config.MODE}")
    logger.info(f"Modo prueba: {config.TEST_MODE_ACTIVE}")

def main():
    """Función principal"""
    print("\n" + "=" * 60)
    print("SEELIE - SISTEMA DE MODERACION")
    print("=" * 60)
    print(f"\nModo: {config.MODE}")
    print(f"Modo prueba: {'ACTIVO' if config.TEST_MODE_ACTIVE else 'INACTIVO'}")
    print(f"Modo silencioso: {'ACTIVO' if config.SILENT_MODE_ACTIVE else 'INACTIVO'}")
    print("\nInicializando...\n")
    
    # Crear aplicación
    application = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    # Comandos admin
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("warn", cmd_warn))
    application.add_handler(CommandHandler("mute", cmd_mute))
    application.add_handler(CommandHandler("unmute", cmd_unmute))
    application.add_handler(CommandHandler("ban", cmd_ban))
    application.add_handler(CommandHandler("checkuser", cmd_checkuser))
    application.add_handler(CommandHandler("history", cmd_history))
    application.add_handler(CommandHandler("trust", cmd_trust))
    application.add_handler(CommandHandler("untrust", cmd_untrust))
    application.add_handler(CommandHandler("forgive", cmd_forgive))
    application.add_handler(CommandHandler("setrisk", cmd_setrisk))
    application.add_handler(CommandHandler("config", cmd_config))
    application.add_handler(CommandHandler("modo", cmd_modo))
    application.add_handler(CommandHandler("done", request_module.cmd_done))
    application.add_handler(CommandHandler("pedidos", request_module.cmd_pedidos))
    
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
    
    print("OK - Seelie esta corriendo...\n")
    print("Presiona Ctrl+C para detener\n")
    
    # Ejecutar bot
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "edited_message", "channel_post",
                         "my_chat_member", "chat_member", "chat_join_request"]
    )

if __name__ == '__main__':
    main()