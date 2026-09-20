"""
SEELIE - Bot con Health Check para Hosting 24/7
Inicia el bot de Telegram y un servidor web para health checks
"""

import os
import threading
import logging
from flask import Flask

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("seelie.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ChatJoinRequestHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
    filters,
    ContextTypes
)

import config
from database.models import db
from database.db_manager import db_manager
from handlers.messages import handle_group_message, handle_new_member, handle_chat_member, handle_join_request
from handlers.callbacks import handle_callback_query
from handlers.inline import inline_query, chosen_inline_result
from handlers.commands import (
    cmd_warn, cmd_mute, cmd_unmute, cmd_ban,
    cmd_checkuser, cmd_history, cmd_trust, cmd_untrust,
    cmd_forgive, cmd_setrisk, cmd_config, cmd_modo,
    cmd_checkfotos, cmd_ayuda, cmd_pedidoincorrecto,
    cmd_pedidoincompleto, cmd_pedidofueraformato, cmd_pedidorepetido,
    cmd_stats, cmd_toppedidos, cmd_scanbiblioteca, cmd_invitar,
    cmd_buscar, cmd_topaportadores, cmd_respaldo, cmd_scanenlaces,
    cmd_directorio, cmd_genero, cmd_recomiendame, cmd_masleidos, cmd_diascierre, cmd_mispedidos, cmd_nopermitir, cmd_sipermitir, cmd_vacaciones, cmd_configlog, cmd_miperfil, cmd_misaportes, cmd_estadisticas, cmd_exportarbiblioteca, cmd_pendientes, cmd_apelaciones, cmd_hoy, cmd_clasicos, cmd_lanzamientos, cmd_panel, cmd_auditoria, cmd_simular, cmd_sos, cmd_get, cmd_bajoperfil, cmd_cmds, cmd_modulos
)
from modules.scheduler import scheduler_module
from modules.requests import request_module

# Flask app para health check
app = Flask(__name__)

@app.route('/')
def health_check():
    return {
        'status': 'ok',
        'bot': 'Seelie',
        'mode': config.MODE,
        'test_mode': config.TEST_MODE_ACTIVE
    }, 200

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "Seelie - Sistema de Moderacion Activo\n\n"
        f"Modo: {config.MODE}\n"
        f"Modo prueba: {'SI' if config.TEST_MODE_ACTIVE else 'NO'}\n\n"
        "Usa /config para ver la configuracion completa."
    )

async def post_init(application):
    """InicializaciÃ³n despuÃ©s de que se crea la aplicaciÃ³n"""
    # Inicializar base de datos
    await db.init()
    
    # Iniciar scheduler con el contexto
    scheduler_module.start(application)
    
    from telegram import BotCommand
    commands = [
        BotCommand("buscar", "ðŸ” Encuentra tu prÃ³ximo libro"),
        BotCommand("directorio", "ðŸ—‚ï¸ Explora el Ã­ndice de autores"),
        BotCommand("pedir", "ðŸ™‹â€â™€ï¸ Pide un libro que no encuentres"),
        BotCommand("clasicos", "ðŸ•°ï¸ Busca libros clÃ¡sicos (<1950)"),
        BotCommand("lanzamientos", "ðŸ†• Busca libros recientes"),
        BotCommand("topaportadores", "ðŸ† Ranking de la comunidad"),
        BotCommand("ayuda", "ðŸ’¡ Manual interactivo del bot")
    ]
    try:
        await application.bot.set_my_commands(commands)
    except Exception as e:
        print(f"Error seteando comandos: {e}")
        
    print(f"OK - Seelie inicializado correctamente")
    print(f"Modo: {config.MODE}")
    print(f"Modo prueba: {config.TEST_MODE_ACTIVE}")

def run_bot():
    """Ejecutar el bot de Telegram"""
    # Crear aplicaciÃ³n
    application = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    # Comandos admin (inglÃ©s y espaÃ±ol)
    application.add_handler(CommandHandler("start", start_command))
    
    # ModeraciÃ³n
    application.add_handler(CommandHandler("warn", cmd_warn))
    application.add_handler(CommandHandler("advertir", cmd_warn))  # espaÃ±ol
    
    application.add_handler(CommandHandler("mute", cmd_mute))
    application.add_handler(CommandHandler("silenciar", cmd_mute))  # espaÃ±ol
    
    application.add_handler(CommandHandler("unmute", cmd_unmute))
    application.add_handler(CommandHandler("desmutear", cmd_unmute))  # espaÃ±ol
    
    application.add_handler(CommandHandler("ban", cmd_ban))
    application.add_handler(CommandHandler("expulsar", cmd_ban))  # espaÃ±ol
    
    # InformaciÃ³n
    application.add_handler(CommandHandler("checkuser", cmd_checkuser))
    application.add_handler(CommandHandler("verusuario", cmd_checkuser))  # espaÃ±ol
    
    application.add_handler(CommandHandler("history", cmd_history))
    application.add_handler(CommandHandler("historial", cmd_history))  # espaÃ±ol
    
    # Trusted
    application.add_handler(CommandHandler("trust", cmd_trust))
    application.add_handler(CommandHandler("confiar", cmd_trust))  # espaÃ±ol
    
    application.add_handler(CommandHandler("untrust", cmd_untrust))
    application.add_handler(CommandHandler("quitarconfianza", cmd_untrust))  # espaÃ±ol
    
    # Perdonar
    application.add_handler(CommandHandler("forgive", cmd_forgive))
    application.add_handler(CommandHandler("perdonar", cmd_forgive))  # espaÃ±ol
    
    # Riesgo y config
    application.add_handler(CommandHandler("setrisk", cmd_setrisk))
    application.add_handler(CommandHandler("config", cmd_config))
    application.add_handler(CommandHandler("ajustes", cmd_config))  # espaÃ±ol
    
    application.add_handler(CommandHandler("modo", cmd_modo))
    
    # Foto
    application.add_handler(CommandHandler("checkfotos", cmd_checkfotos))
    application.add_handler(CommandHandler("revisarfotos", cmd_checkfotos))  # espaÃ±ol
    
    # Ayuda
    application.add_handler(CommandHandler("ayuda", cmd_ayuda))
    application.add_handler(CommandHandler("invitar", cmd_invitar))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("toppedidos", cmd_toppedidos))
    application.add_handler(CommandHandler("estadisticaspedidos", cmd_toppedidos))
    application.add_handler(CommandHandler("scanbiblioteca", cmd_scanbiblioteca))
    application.add_handler(CommandHandler("duplicados", cmd_scanbiblioteca))
    application.add_handler(CommandHandler("buscar", cmd_buscar))
    application.add_handler(CommandHandler("get", cmd_get))
    application.add_handler(CommandHandler("cmds", cmd_cmds))
    application.add_handler(CommandHandler("modulos", cmd_modulos))
    application.add_handler(CommandHandler("bajoperfil", cmd_bajoperfil))
    application.add_handler(CommandHandler("topaportadores", cmd_topaportadores))
    application.add_handler(CommandHandler("respaldo", cmd_respaldo))
    application.add_handler(CommandHandler("backupbd", cmd_respaldo))
    application.add_handler(CommandHandler("scanenlaces", cmd_scanenlaces))

    
    # Pedidos
    application.add_handler(CommandHandler("done", request_module.cmd_done))
    application.add_handler(CommandHandler("listo", request_module.cmd_done))  # espaÃ±ol
    
    application.add_handler(CommandHandler("pedidos", request_module.cmd_pedidos))
    application.add_handler(CommandHandler("solicitudes", request_module.cmd_pedidos))  # espaÃ±ol
    
    # Pedido incorrecto - variantes (revisiÃ³n manual por admin)
    application.add_handler(CommandHandler("pedidoincorrecto", cmd_pedidoincorrecto))
    application.add_handler(CommandHandler("pedidoincompleto", cmd_pedidoincompleto))
    application.add_handler(CommandHandler("pedidofueraformato", cmd_pedidofueraformato))
    application.add_handler(CommandHandler("pedidorepetido", cmd_pedidorepetido))
    
    application.add_handler(CommandHandler("directorio", cmd_directorio))
    application.add_handler(CommandHandler("genero", cmd_genero))
    application.add_handler(CommandHandler("recomiendame", cmd_recomiendame))
    application.add_handler(CommandHandler("masleidos", cmd_masleidos))
    application.add_handler(CommandHandler("diascierre", cmd_diascierre))
    application.add_handler(CommandHandler("mispedidos", cmd_mispedidos))
    application.add_handler(CommandHandler("nopermitir", cmd_nopermitir))
    application.add_handler(CommandHandler("sipermitir", cmd_sipermitir))
    application.add_handler(CommandHandler("vacaciones", cmd_vacaciones))
    application.add_handler(CommandHandler("configlog", cmd_configlog))
    application.add_handler(CommandHandler("miperfil", cmd_miperfil))
    application.add_handler(CommandHandler("misaportes", cmd_misaportes))
    application.add_handler(CommandHandler("estadisticas", cmd_estadisticas))
    application.add_handler(CommandHandler("auditoria", cmd_auditoria))
    application.add_handler(CommandHandler("simular", cmd_simular))
    application.add_handler(CommandHandler("sos", cmd_sos))
    application.add_handler(CommandHandler("exportarbiblioteca", cmd_exportarbiblioteca))
    application.add_handler(CommandHandler("pendientes", cmd_pendientes))
    application.add_handler(CommandHandler("apelaciones", cmd_apelaciones))
    application.add_handler(CommandHandler("hoy", cmd_hoy))
    application.add_handler(CommandHandler("clasicos", cmd_clasicos))
    application.add_handler(CommandHandler("lanzamientos", cmd_lanzamientos))
    application.add_handler(CommandHandler("panel", cmd_panel))
    
    # Manejador de DM interactivo /pedido (ConversationHandler) - inglÃ©s y espaÃ±ol
    application.add_handler(request_module.get_conversation_handler())
    # Alias espaÃ±ol para /pedido
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('pedir', request_module.cmd_pedido)],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_module.recv_tipo_serie)],
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_module.recv_titulo)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_module.recv_autor)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_module.recv_idioma)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_module.recv_formato)],
            5: [CallbackQueryHandler(request_module.handle_req_callback, pattern='^req_')],
        },
        fallbacks=[CommandHandler('cancelar', request_module.cancel_pedido)],
        per_user=True,
        per_chat=True
    ))
    
    # Handler de nuevos miembros (mensajes de servicio)
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_member
    ))
    
    # Handler para solicitudes de uniÃ³n
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    # Handler para actualizaciones de estado de miembros (ej. uso de links)
    application.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.CHAT_MEMBER))
    
    # Handler de mensajes del grupo
    application.add_handler(MessageHandler(
        filters.ChatType.SUPERGROUP & ~filters.COMMAND,
        handle_group_message
    ))
    
    # Handler de mensajes privados (Fase 5: ReenvÃ­os y OCR)
    from handlers.messages import handle_private_message
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_private_message
    ))
    
    # Handler para botones inline
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Handler para busquedas inline (@bot libro)
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    
    print("OK - Seelie esta corriendo...")
    
    # [FASE 5] Servidor Web Falso para plataformas gratuitas (Render)
    import os
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(b"Selene is awake and watching!")
            
    def run_dummy_server():
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(('0.0.0.0', port), DummyHandler)
        server.serve_forever()
        
    if os.environ.get("RENDER") or os.environ.get("PORT"):
        threading.Thread(target=run_dummy_server, daemon=True).start()
        print("Servidor web iniciado para Render.")
    
    # Ejecutar bot
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "edited_message", "channel_post",
                         "my_chat_member", "chat_member", "chat_join_request",
                         "callback_query", "inline_query", "chosen_inline_result"]
    )

def main():
    """FunciÃ³n principal - inicia bot y servidor web"""
    print("\n" + "=" * 60)
    print("SEELIE - SISTEMA DE MODERACION")
    print("=" * 60)
    print(f"\nModo: {config.MODE}")
    print(f"Modo prueba: {'ACTIVO' if config.TEST_MODE_ACTIVE else 'INACTIVO'}")
    print(f"Modo silencioso: {'ACTIVO' if config.SILENT_MODE_ACTIVE else 'INACTIVO'}")
    print("\nInicializando...\n")
    
    # Iniciar bot en thread separado
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Iniciar servidor Flask para health checks
    port = int(os.environ.get('PORT', 5000))
    print(f"Health check server en puerto {port}")
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
