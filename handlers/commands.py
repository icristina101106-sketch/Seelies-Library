"""
Handler de Comandos Admin
Comandos de administración del bot
"""

from telegram import Update
from telegram.ext import ContextTypes
import config
from database.db_manager import db_manager
from utils.formatters import formatter
from datetime import datetime, timedelta

async def _delete_cmd(update):
    """Borrar el mensaje del comando y devolver chat_id y thread_id"""
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id
    try:
        await update.message.delete()
    except:
        pass
    return chat_id, thread_id

async def _send(context, chat_id, thread_id, text, parse_mode=None):
    """Enviar mensaje al chat/thread"""
    await context.bot.send_message(
        chat_id=chat_id, message_thread_id=thread_id,
        text=text, parse_mode=parse_mode
    )

async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /warn - Advertencia manual (soporta reply)"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    # Soporte para reply
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        reason = ' '.join(context.args) if context.args else "Advertencia manual"
    elif not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /warn <user_id> [razón] (o responde a un mensaje)")
        return
    else:
        try:
            user_id = int(context.args[0])
            reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Advertencia manual"
        except ValueError:
            await _send(context, chat_id, thread_id, "❌ ID de usuario inválido")
            return
    
    await db_manager.add_warning(
        user_id=user_id,
        warning_type='manual',
        severity='media',
        message_text=reason,
        action_taken='warning'
    )
    
    # Registrar en log de auditoría
    await db_manager.add_audit_log(
        admin_id=update.effective_user.id,
        admin_username=update.effective_user.username,
        action_type='warn',
        target_user_id=user_id,
        reason=reason
    )
    
    await _send(context, chat_id, thread_id, f"✅ Warning agregada a usuario {user_id}")
    
    # Borrar mensaje infractor si fue reply
    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.delete()
        except Exception:
            pass
    
    # Aplicar castigo progresivo
    user_data = await db_manager.get_user(user_id)
    from modules.warnings import warnings_module
    await warnings_module.apply_progressive_punishment(user_id, user_data, context)

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /mute - Mutear usuario (soporta reply)"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    # Soporte para reply
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        minutes = int(context.args[0]) if context.args else 60
    elif not context.args or len(context.args) < 2:
        await _send(context, chat_id, thread_id, "Uso: /mute <user_id> <minutos> (o responde a un mensaje)")
        return
    else:
        try:
            user_id = int(context.args[0])
            minutes = int(context.args[1])
        except ValueError:
            await _send(context, chat_id, thread_id, "❌ Parámetros inválidos")
            return
    
    until_date = datetime.now() + timedelta(minutes=minutes)
    await context.bot.restrict_chat_member(
        chat_id=config.GROUP_ID,
        user_id=user_id,
        permissions={"can_send_messages": False},
        until_date=until_date
    )
    
    await db_manager.log_moderation_action(
        user_id=user_id,
        action_type='mute',
        reason='Manual',
        duration=minutes,
        auto_action=False,
        admin_id=update.effective_user.id
    )
    
    # Registrar en audit log
    await db_manager.add_audit_log(
        admin_id=update.effective_user.id,
        admin_username=update.effective_user.username,
        action_type='mute',
        target_user_id=user_id,
        reason=f"Mute {minutes} min"
    )
    
    await _send(context, chat_id, thread_id, f"✅ Usuario {user_id} muteado por {minutes} minutos")
    
    # Borrar mensaje infractor si fue reply
    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.delete()
        except Exception:
            pass

async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /unmute - Desmutear usuario"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /unmute <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        
        await context.bot.restrict_chat_member(
            chat_id=config.GROUP_ID,
            user_id=user_id,
            permissions={
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True
            }
        )
        
        # Registrar en audit log
        await db_manager.add_audit_log(
            admin_id=update.effective_user.id,
            admin_username=update.effective_user.username,
            action_type='unmute',
            target_user_id=user_id,
            reason="Desmute manual"
        )
        
        await _send(context, chat_id, thread_id, f"✅ Usuario {user_id} desmuteado")
        
    except ValueError:
        await _send(context, chat_id, thread_id, "❌ ID de usuario inválido")

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ban - Banear usuario (soporta reply)"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    # Soporte para reply
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        reason = ' '.join(context.args) if context.args else "Ban manual"
    elif not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /ban <user_id> [razón] (o responde a un mensaje)")
        return
    else:
        try:
            user_id = int(context.args[0])
            reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Ban manual"
        except ValueError:
            await _send(context, chat_id, thread_id, "❌ ID de usuario inválido")
            return
            
    # Resumen antes de ban
    user_data = await db_manager.get_user(user_id)
    if not user_data:
        await _send(context, chat_id, thread_id, "❌ Usuario no encontrado.")
        return
        
    msg = f"⚠️ **CONFIRMACIÓN DE BANEO** ⚠️\n\n"
    msg += f"**Usuario:** @{user_data.get('username') or user_data.get('first_name')}\n"
    msg += f"**Motivo:** {reason}\n\n"
    msg += f"**Historial:**\n"
    msg += f"• Mensajes: {user_data.get('message_count', 0)}\n"
    msg += f"• Aportes: {user_data.get('contributions', 0)}\n"
    msg += f"• Advertencias: {user_data.get('warnings_count', 0)}\n"
    msg += f"• Riesgo actual: {user_data.get('risk_score', 0)}\n\n"
    msg += "¿Estás seguro de que deseas proceder?"
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar Ban", callback_data=f"banconfirm|{user_id}|{reason}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"bancancel|{user_id}")]
    ])
    
    # Save the message id to delete it later if it's a reply
    if update.message.reply_to_message:
        context.user_data['ban_target_msg_id'] = update.message.reply_to_message.message_id
        
    await _send(context, chat_id, thread_id, msg, reply_markup=keyboard)

async def cmd_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cmds - Lista absolutamente todos los comandos (Fase 5)"""
    chat_id, thread_id = await _delete_cmd(update)
    is_admin = update.effective_user.id in config.ADMIN_IDS
    
    msg = "📚 **LISTA COMPLETA DE COMANDOS DE SELENE** 📚\n\n"
    
    msg += "👥 **PARA TODOS LOS USUARIOS:**\n"
    msg += "`/buscar [nombre]` - Buscar un libro\n"
    msg += "`/pedido` - Asistente para pedir libros (por DM)\n"
    msg += "`/mispedidos` - Tu historial de peticiones\n"
    msg += "`/miperfil` - Tu rango, estadísticas y antigüedad\n"
    msg += "`/misaportes` - Lista de libros que has subido\n"
    msg += "`/genero [nombre]` - Buscar libros por género literario\n"
    msg += "`/recomiendame` - Selene te sugiere lecturas\n"
    msg += "`/masleidos` - El top de libros más populares\n"
    msg += "`/directorio` - Búsqueda alfabética por autores\n"
    msg += "`/clasicos` - Libros anteriores a 1950\n"
    msg += "`/lanzamientos` - Los libros más nuevos del grupo\n"
    msg += "`/estadisticas` - Datos públicos del servidor\n"
    msg += "`/pendientes` - Ver la lista de espera de pedidos\n"
    msg += "`/ayuda` - Menú interactivo de ayuda\n\n"
    
    if is_admin:
        msg += "👑 **COMANDOS DE ADMINISTRADOR:**\n"
        msg += "`/panel` - Panel de control con botones\n"
        msg += "`/ban`, `/mute`, `/warn`, `/kick` - Sancionar\n"
        msg += "`/forgive`, `/unmute` - Perdonar sanciones\n"
        msg += "`/trust`, `/untrust` - Gestionar rango de confianza\n"
        msg += "`/setrisk [1-5]` - Ajustar nivel de amenaza manual\n"
        msg += "`/checkuser` / `/history` - Auditoría de miembros\n"
        msg += "`/simular ban` - Ver qué pasaría sin hacerlo real\n"
        msg += "`/sos` - 🚨 Pánico: Silencia a todos los usuarios\n"
        msg += "`/bajoperfil` - 🛡️ Activa rechazo masivo de entradas\n"
        msg += "`/auditoria` - Verifica si Selene tiene permisos\n"
        msg += "`/scanbiblioteca` - Escanea PDFs duplicados en el chat\n"
        msg += "`/scanenlaces` - Revisa si hay links rotos\n"
        msg += "`/respaldo` / `/exportarbiblioteca` - Descargar DB\n"
        msg += "`/nopermitir` / `/sipermitir` - Blacklist de Copyright\n"
        msg += "`/diascierre` / `/vacaciones` - Ajustes de inactividad\n"
        msg += "`/modulos` - 🎛️ Apagar o prender áreas enteras del bot\n"
        msg += "`/configlog` - Ver registro de cambios de admins\n"
        msg += "`/hoy` - Resumen diario de moderación\n"
        msg += "`/apelaciones` - Ver castigos reclamados\n"
        msg += "`/topaportadores` - Ranking interno de subidas\n"
        msg += "`/pedidoincompleto`, `/pedidorepetido` - Modera peticiones\n\n"
        msg += "📌 *Tip: Selene también actúa si le reenvías un mensaje de spam o le mandas la captura de perfil de un usuario (OCR).* \n"
        
    await _send(context, chat_id, thread_id, msg)

async def cmd_modulos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /modulos - Apagar o prender áreas enteras del bot"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    from modules import toggles
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    state = toggles.load_toggles()
    
    def btn_text(name, is_on):
        return f"🟢 {name}" if is_on else f"🔴 {name} (Apagado)"
        
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_text("Moderación y Filtros", state["moderacion"]), callback_data="toggle_moderacion")],
        [InlineKeyboardButton(btn_text("Biblioteca y Subidas", state["biblioteca"]), callback_data="toggle_biblioteca")],
        [InlineKeyboardButton(btn_text("Sistema de Pedidos", state["pedidos"]), callback_data="toggle_pedidos")],
        [InlineKeyboardButton(btn_text("Entradas y Auto-Aceptar", state["entradas"]), callback_data="toggle_entradas")],
        [InlineKeyboardButton("✅ Listo", callback_data="toggle_done")]
    ])
    
    msg = "🎛️ **Panel de Módulos de Selene**\n\nApaga o prende funciones enteras para probar cosas sin afectar al grupo."
    await _send(context, chat_id, thread_id, msg, reply_markup=keyboard)

async def cmd_checkuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /checkuser - Ver información de usuario"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /checkuser <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        
        user_data = await db_manager.get_user(user_id)
        if not user_data:
            await _send(context, chat_id, thread_id, "❌ Usuario no encontrado")
            return
        
        # Verificar foto de perfil real desde Telegram
        try:
            photos = await context.bot.get_user_profile_photos(user_id, limit=1)
            real_has_photo = photos.total_count > 0 or bool(user_data['has_photo'])
        except:
            real_has_photo = bool(user_data['has_photo'])
        
        # Obtener info real del chat member
        try:
            member = await context.bot.get_chat_member(config.GROUP_ID, user_id)
            real_name = member.user.first_name or user_data['first_name']
            real_username = member.user.username or user_data['username']
        except:
            real_name = user_data['first_name']
            real_username = user_data['username']
        
        user_data['has_photo'] = real_has_photo
        user_data['first_name'] = real_name
        user_data['username'] = real_username
        
        warnings = await db_manager.get_user_warnings(user_id, limit=5)
        actions = await db_manager.get_user_history(user_id, limit=5)
        quality_data = await db_manager.get_member_quality_data(user_id)
        
        info = formatter.format_checkuser_info(user_data, warnings, [], actions, quality_data)
        await _send(context, chat_id, thread_id, info)
        
    except ValueError:
        await _send(context, chat_id, thread_id, "❌ ID de usuario inválido")

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /history - Ver historial de usuario"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /history <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        
        actions = await db_manager.get_user_history(user_id, limit=20)
        if not actions:
            await _send(context, chat_id, thread_id, "No hay historial para este usuario")
            return
        
        history = f"📋 HISTORIAL DE USUARIO {user_id}\n"
        history += "=" * 40 + "\n\n"
        
        for action in actions:
            history += f"• {action['action_type'].upper()}\n"
            history += f"  Razón: {action['reason']}\n"
            history += f"  Fecha: {action['timestamp'][:16]}\n"
            if action['duration']:
                history += f"  Duración: {action['duration']} min\n"
            history += "\n"
        
        await _send(context, chat_id, thread_id, history)
        
    except ValueError:
        await _send(context, chat_id, thread_id, "❌ ID de usuario inválido")

async def cmd_trust(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /trust - Promover a trusted"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /trust <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        
        await db_manager.promote_to_trusted(user_id)
        
        # Registrar en audit log
        await db_manager.add_audit_log(
            admin_id=update.effective_user.id,
            admin_username=update.effective_user.username,
            action_type='trust',
            target_user_id=user_id,
            reason="Promovido a trusted"
        )
        
        await _send(context, chat_id, thread_id, f"✅ Usuario {user_id} promovido a trusted")
        
    except ValueError:
        await _send(context, chat_id, thread_id, "❌ ID de usuario inválido")

async def cmd_untrust(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /untrust - Quitar trusted"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /untrust <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Manual"
        
        await db_manager.demote_from_trusted(user_id, reason)
        
        # Registrar en audit log
        await db_manager.add_audit_log(
            admin_id=update.effective_user.id,
            admin_username=update.effective_user.username,
            action_type='untrust',
            target_user_id=user_id,
            reason=f"Trusted removido: {reason}"
        )
        
        await _send(context, chat_id, thread_id, f"✅ Trusted removido de usuario {user_id}")
        
    except ValueError:
        await _send(context, chat_id, thread_id, "❌ ID de usuario inválido")

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ayuda - Dashboard interactivo de comandos"""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    chat_id, thread_id = await _delete_cmd(update)
    
    msg = (
        "👋 **¡Hola! Soy Selene, tu bibliotecaria.**\n\n"
        "Puedo ayudarte a encontrar libros, organizar la biblioteca y mantener "
        "nuestra comunidad limpia. Selecciona qué quieres hacer hoy:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Soy Lector", callback_data="help_lector")],
        [InlineKeyboardButton("🤝 Quiero Aportar", callback_data="help_aportar")],
        [InlineKeyboardButton("🛡️ Soy Admin", callback_data="help_admin")]
    ])
    
    if update.effective_chat.type == 'private':
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard)
    else:
        bot_msg = await _send(context, chat_id, thread_id, msg, parse_mode='Markdown', reply_markup=keyboard)
        import asyncio
        async def delete_later(c_id, m_id):
            await asyncio.sleep(300)
            try:
                await context.bot.delete_message(chat_id=c_id, message_id=m_id)
            except:
                pass
        if bot_msg:
            asyncio.create_task(delete_later(chat_id, bot_msg.message_id))

async def cmd_forgive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /forgive - Perdonar warning"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /forgive <warning_id>")
        return
    
    try:
        warning_id = int(context.args[0])
        
        success = await db_manager.revoke_warning(warning_id, update.effective_user.id)
        if success:
            # Registrar en audit log
            await db_manager.add_audit_log(
                admin_id=update.effective_user.id,
                admin_username=update.effective_user.username,
                action_type='forgive',
                target_user_id=user_id if 'user_id' in locals() else None,
                reason=f"Warning {warning_id} revocada"
            )
            await _send(context, chat_id, thread_id, f"✅ Warning {warning_id} revocada")
        else:
            await _send(context, chat_id, thread_id, "❌ Warning no encontrada")
        
    except ValueError:
        await _send(context, chat_id, thread_id, "❌ ID de warning inválido")

async def cmd_setrisk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /setrisk - Ajustar riesgo manualmente"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 2:
        await _send(context, chat_id, thread_id, "Uso: /setrisk <user_id> <puntos>")
        return
    
    try:
        user_id = int(context.args[0])
        points = int(context.args[1])
        
        await db_manager.set_risk_score(user_id, points)
        await _send(context, chat_id, thread_id, f"✅ Riesgo de usuario {user_id} ajustado a {points}")
        
    except ValueError:
        await _send(context, chat_id, thread_id, "❌ Parámetros inválidos")

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /panel - Panel visual de administrador"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    chat_id, thread_id = await _delete_cmd(update)
    
    msg = "🎛️ **Panel de Administración**\n\n¿Qué necesitas hacer, Jefe?"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="panel_stats")],
        [InlineKeyboardButton("💾 Descargar Base de Datos", callback_data="panel_backup")],
        [InlineKeyboardButton("📝 Recordar Comandos", callback_data="panel_cmds")],
        [InlineKeyboardButton("⚙️ Configuración Actual", callback_data="panel_config")],
        [InlineKeyboardButton("📋 Ver Errores (Logs)", callback_data="panel_logs")]
    ])
    
    if update.effective_chat.type == 'private':
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard)
    else:
        bot_msg = await _send(context, chat_id, thread_id, msg, parse_mode='Markdown', reply_markup=keyboard)
        import asyncio
        async def delete_later(c_id, m_id):
            await asyncio.sleep(300)
            try:
                await context.bot.delete_message(chat_id=c_id, message_id=m_id)
            except:
                pass
        if bot_msg:
            asyncio.create_task(delete_later(chat_id, bot_msg.message_id))

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stats - Ver estadísticas del grupo"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    # Obtener estadísticas
    stats = await db_manager.get_stats()
    
    # Formatear mensaje
    msg = "📊 **ESTADÍSTICAS DEL GRUPO**\n"
    msg += "=" * 35 + "\n\n"
    
    msg += "👥 **Usuarios:**\n"
    msg += f"  Total: {stats['total_users']}\n"
    msg += f"  Activos: {stats['active_users']}\n"
    msg += f"  Trusted: {stats['trusted_users']}\n"
    msg += f"  Baneados: {stats['total_bans']}\n\n"
    
    msg += "📚 **Pedidos:**\n"
    msg += f"  Total: {stats['total_requests']}\n"
    msg += f"  Pendientes: {stats['pending_requests']}\n"
    msg += f"  Atendidos: {stats['completed_requests']}\n\n"
    
    msg += "⚠️ **Moderación:**\n"
    msg += f"  Warnings totales: {stats['total_warnings']}\n"
    msg += f"  Warnings esta semana: {stats['warnings_this_week']}\n"
    
    await _send(context, chat_id, thread_id, msg, parse_mode='Markdown')

async def cmd_toppedidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /toppedidos - Ver estadísticas de los libros más solicitados"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    stats = await db_manager.get_top_requests_stats()
    
    msg = "🏆 **ESTADÍSTICAS DE PEDIDOS**\n"
    msg += "=" * 35 + "\n\n"
    
    msg += f"📅 **Últimos 30 días:** {stats['month_requests']} pedidos\n\n"
    
    msg += "📚 **Top 10 Más Solicitados:**\n"
    if stats['top_books']:
        for i, book in enumerate(stats['top_books'], 1):
            title = book['norm_title'].title() if book['norm_title'] else "Desconocido"
            msg += f"  {i}. {title} ({book['count']})\n"
    else:
        msg += "  No hay datos suficientes.\n"
        
    msg += "\n🌐 **Idiomas:**\n"
    for lang in stats['lang_stats']:
        msg += f"  • {lang['language']}: {lang['count']}\n"
        
    msg += "\n📄 **Formatos:**\n"
    for fmt in stats['format_stats']:
        msg += f"  • {fmt['format']}: {fmt['count']}\n"
        
    await _send(context, chat_id, thread_id, msg, parse_mode='Markdown')

async def cmd_scanbiblioteca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /scanbiblioteca - Buscar duplicados en la biblioteca"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    topic_filter = context.args[0].lower() if context.args else None
    
    await _send(context, chat_id, thread_id, "🔍 Escaneando biblioteca, esto puede tardar un momento...")
    
    if topic_filter in ["esp", "español"]:
        files = await db_manager.get_library_files('biblioteca_español')
    elif topic_filter in ["ing", "inglés", "ingles"]:
        files = await db_manager.get_library_files('biblioteca_inglés')
    else:
        files = await db_manager.get_library_files()
        
    if not files:
        await _send(context, chat_id, thread_id, "❌ No hay archivos registrados en la base de datos.")
        return
        
    from utils.text_analysis import text_analyzer
    from utils.formatters import formatter
    
    duplicates = []
    # Comparar todos contra todos (O(N^2) pero N es pequeño típicamente)
    for i, f1 in enumerate(files):
        if not f1['file_name']:
            continue
        for f2 in files[i+1:]:
            if not f2['file_name'] or f1['topic_name'] != f2['topic_name']:
                continue
                
            similarity, match_type = text_analyzer.compare_filenames(f1['file_name'], f2['file_name'])
            
            if match_type in ('exacto', 'probable'):
                dup_info = {
                    'file_name_1': f1['file_name'],
                    'file_name_2': f2['file_name'],
                    'message_id_1': f1['message_id'],
                    'message_id_2': f2['message_id'],
                    'similarity_score': similarity,
                    'match_type': match_type
                }
                duplicates.append(dup_info)
                
                # Guardar en base de datos
                await db_manager.save_duplicate(
                    file_name_1=f1['file_name'],
                    file_name_2=f2['file_name'],
                    message_id_1=f1['message_id'],
                    message_id_2=f2['message_id'],
                    similarity_score=similarity,
                    match_type=match_type
                )
                
    report = formatter.format_duplicate_report(duplicates)
    await _send(context, chat_id, thread_id, report)

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /config - Ver configuración actual"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    cfg = f"⚙️ CONFIGURACIÓN ACTUAL\n"
    cfg += "=" * 40 + "\n\n"
    cfg += f"Modo: {config.MODE}\n"
    cfg += f"Modo prueba: {'✅' if config.TEST_MODE_ACTIVE else '❌'}\n"
    cfg += f"Modo silencioso: {'✅' if config.SILENT_MODE_ACTIVE else '❌'}\n\n"
    cfg += f"Max warnings: {config.MAX_WARNINGS_BEFORE_BAN}\n"
    cfg += f"Umbral riesgo ban: {config.RISK_SCORE_BAN_THRESHOLD}\n"
    cfg += f"Flood: {config.FLOOD_MESSAGE_COUNT} msgs en {config.FLOOD_TIME_SECONDS}s\n"
    cfg += f"Mute 1: {config.MUTE_DURATION_1} min\n"
    cfg += f"Mute 2: {config.MUTE_DURATION_2} min\n"
    cfg += f"Mute 3: {config.MUTE_DURATION_3} min\n"
    
    await _send(context, chat_id, thread_id, cfg)

async def cmd_modo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /modo - Cambiar modo del bot"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 1:
        await _send(context, chat_id, thread_id, "Uso: /modo <produccion|prueba|silencioso>")
        return
    
    mode = context.args[0].lower()
    
    if mode == "produccion":
        config.MODE = "produccion"
        config.TEST_MODE_ACTIVE = False
        config.SILENT_MODE_ACTIVE = False
        await _send(context, chat_id, thread_id, "✅ Modo PRODUCCIÓN activado")
    elif mode == "prueba":
        config.MODE = "prueba"
        config.TEST_MODE_ACTIVE = True
        config.SILENT_MODE_ACTIVE = False
        await _send(context, chat_id, thread_id, "✅ Modo PRUEBA activado (detecta pero no castiga)")
    elif mode == "silencioso":
        config.MODE = "silencioso"
        config.TEST_MODE_ACTIVE = False
        config.SILENT_MODE_ACTIVE = True
        await _send(context, chat_id, thread_id, "✅ Modo SILENCIOSO activado (actúa sin mensajes)")
    else:
        await _send(context, chat_id, thread_id, "❌ Modo inválido. Usa: produccion, prueba o silencioso")

async def cmd_checkfotos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /checkfotos - Revisar usuarios sin foto de perfil"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    await _send(context, chat_id, thread_id, "🔍 Revisando fotos de perfil... espera un momento.")
    
    # Obtener todos los usuarios conocidos de la BD
    import aiosqlite
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, username, first_name FROM users WHERE is_banned = 0") as cursor:
            users = [dict(row) for row in await cursor.fetchall()]
    
    sin_foto = []
    for user in users:
        try:
            photos = await context.bot.get_user_profile_photos(user['user_id'], limit=1)
            if photos.total_count == 0:
                name = f"@{user['username']}" if user['username'] else user['first_name'] or f"ID:{user['user_id']}"
                sin_foto.append(name)
        except:
            pass
    
    if sin_foto:
        msg = f"📷 **USUARIOS SIN FOTO DE PERFIL** ({len(sin_foto)})\n"
        msg += "=" * 35 + "\n\n"
        for name in sin_foto:
            msg += f"• {name}\n"
        msg += f"\n💡 El sistema avisa automáticamente a nuevos miembros sin foto."
        await _send(context, chat_id, thread_id, msg, parse_mode='Markdown')
    else:
        await _send(context, chat_id, thread_id, "✅ Todos los usuarios conocidos tienen foto de perfil.")


async def _handle_invalid_request(update: Update, context: ContextTypes.DEFAULT_TYPE, command_name: str, warning_type: str, custom_message_prefix: str = None):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    # Debe ser respuesta a un mensaje
    if not update.message or not update.message.reply_to_message:
        await _send(context, chat_id, thread_id, f"⚠️ Usa: /{command_name} respondiendo al mensaje del pedido mal hecho")
        return
    
    target_msg = update.message.reply_to_message
    target_user = target_msg.from_user
    text = target_msg.text or ""
    
    # Verificar si hay razón personalizada
    custom_reason = ' '.join(context.args) if context.args else None
    
    if custom_reason:
        # Usar razón personalizada proporcionada por el admin
        missing_str = custom_reason
    else:
        # Detectar automáticamente qué le falta (solo útil para incompleto/incorrecto)
        from utils.text_analysis import text_analyzer
        data = text_analyzer.extract_request_data(text)
        is_valid, missing = text_analyzer.validate_request_format(data)
        
        if is_valid and warning_type in ['pedido_incorrecto', 'pedido_incompleto']:
            await _send(context, chat_id, thread_id, "✅ El formato de este pedido parece correcto. No se aplicó sanción.")
            return
        
        missing_str = ', '.join(missing) if missing else "Revisión manual requerida"
    
    from utils.formatters import formatter
    base_edu_msg = formatter.format_request_incorrect_message(warning_type.replace('pedido_', ''))
    
    # 1. Dar warning al usuario
    await db_manager.add_warning(
        user_id=target_user.id,
        warning_type=warning_type,
        severity='baja',
        message_text=f"{base_edu_msg} Razón: {missing_str}",
        action_taken='warning'
    )
    
    # Registrar en audit log
    await db_manager.add_audit_log(
        admin_id=update.effective_user.id,
        admin_username=update.effective_user.username,
        action_type=command_name,
        target_user_id=target_user.id,
        target_username=target_user.username,
        reason=f"{base_edu_msg} Razón: {missing_str}",
        chat_id=chat_id,
        message_id=target_msg.message_id
    )
    
    # 2. Responder al usuario mencionando qué falta
    warning_msg = (
        f"⚠️ @{target_user.username or target_user.first_name}, {base_edu_msg}\n\n"
    )
    if custom_message_prefix:
        warning_msg += custom_message_prefix + "\n\n"
    elif missing_str and missing_str != "Revisión manual requerida":
        warning_msg += f"Te falta: **{missing_str}**\n\n"
        
    warning_msg += (
        f"💡 Usa /pedido para hacerlo bien paso a paso y evitar más warnings.\n\n"
        f"📋 Formato correcto:\n"
        f"```\nTítulo: nombre del libro\n"
        f"Autor: nombre del autor\n"
        f"Idioma: Español/Inglés\n"
        f"Formato: PDF/EPUB/Ambos\n```"
    )
    
    sent_warning = await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=warning_msg,
        parse_mode='Markdown'
    )
    
    # 3. Programar borrado del mensaje original en 12 horas
    from datetime import datetime, timedelta
    delete_time = datetime.now() + timedelta(hours=12)
    
    # Guardar en BD para que el scheduler lo borre
    await db_manager.schedule_message_deletion(
        message_id=target_msg.message_id,
        chat_id=chat_id,
        thread_id=thread_id,
        delete_at=delete_time,
        reason=warning_type
    )
    
    # Confirmar al admin
    await _send(
        context, chat_id, thread_id,
        f"✅ Pedido de @{target_user.username or target_user.first_name} marcado como {warning_type}.\n"
        f"Razón: {missing_str}\n"
        f"Warning aplicado. Mensaje se borrará en 12h (a las {delete_time.strftime('%H:%M')})."
    )
    
    # Aplicar castigo progresivo si corresponde
    user_data = await db_manager.get_user(target_user.id)
    from modules.warnings import warnings_module
    await warnings_module.apply_progressive_punishment(target_user.id, user_data, context)

async def cmd_pedidoincorrecto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_invalid_request(update, context, "pedidoincorrecto", "pedido_incorrecto")

async def cmd_pedidoincompleto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_invalid_request(update, context, "pedidoincompleto", "pedido_incompleto")

async def cmd_pedidofueraformato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_invalid_request(update, context, "pedidofueraformato", "pedido_fuera_formato")

async def cmd_pedidorepetido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_invalid_request(update, context, "pedidorepetido", "pedido_repetido", custom_message_prefix="Este libro ya está en la biblioteca o fue pedido recientemente. Por favor, usa el buscador antes de pedir.")

async def cmd_auditoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /auditoria - Ver log de auditoría"""
    # Log a archivo para debugging
    with open('bot_debug.log', 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now()}] cmd_auditoria called by {update.effective_user.id}\n")
    
    if update.effective_user.id not in config.ADMIN_IDS:
        with open('bot_debug.log', 'a', encoding='utf-8') as f:
            f.write(f"  User not in ADMIN_IDS: {config.ADMIN_IDS}\n")
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    
    with open('bot_debug.log', 'a', encoding='utf-8') as f:
        f.write(f"  chat_id={chat_id}, thread_id={thread_id}\n")
    
    # Parsear argumentos
    args = context.args if context.args else []
    target_user_id = None
    action_type = None
    
    for arg in args:
        if arg.startswith('@'):
            # Buscar por username (simplificado - buscar en BD)
            pass
        elif arg.isdigit():
            target_user_id = int(arg)
        elif arg in ['warn', 'ban', 'unban', 'mute', 'unmute', 'delete', 'pedidoincorrecto']:
            action_type = arg
    
    # Obtener log (últimas 20 entradas)
    logs = await db_manager.get_audit_log(
        target_user_id=target_user_id,
        action_type=action_type,
        limit=20
    )
    
    if not logs:
        await _send(context, chat_id, thread_id, "📭 No hay registros en el log de auditoría.")
        return
    
    # Formatear salida
    msg = "📋 **LOG DE AUDITORÍA** (últimas 20)\n"
    msg += "=" * 40 + "\n\n"
    
    for entry in logs:
        timestamp = entry['timestamp'][:16] if entry['timestamp'] else '?'
        admin = entry['admin_username'] or f"ID:{entry['admin_id']}"
        action = entry['action_type'].upper()
        target = entry['target_username'] or f"ID:{entry['target_user_id']}" if entry['target_user_id'] else '-'
        reason = entry['reason'] or 'Sin razón'
        
        msg += f"• `{timestamp}`\n"
        msg += f"  **{admin}** → {action}\n"
        if target != '-':
            msg += f"  Sobre: {target}\n"
        msg += f"  Razón: {reason}\n\n"
    
    await _send(context, chat_id, thread_id, msg, parse_mode='Markdown')

async def cmd_invitar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /invitar - Generar link de invitación único"""
    # Solo admins o trusted pueden usar este comando
    user_id = update.effective_user.id
    user_data = await db_manager.get_user(user_id)
    
    if user_id not in config.ADMIN_IDS and (not user_data or user_data.get('status') != 'trusted'):
        # Silencioso si no tienen permiso
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    # Generar link que se puede usar 1 vez
    try:
        from datetime import timedelta
        expire_date = datetime.now() + timedelta(days=1)
        
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=config.GROUP_ID,
            member_limit=1,
            expire_date=expire_date,
            creates_join_request=True
        )
        
        # Guardar en BD
        await db_manager.save_invite_link(invite_link.invite_link, user_id)
        
        msg = "🎟️ **LINK DE INVITACIÓN GENERADO**\n\n"
        msg += f"`{invite_link.invite_link}`\n\n"
        msg += "⚠️ Este link:\n"
        msg += "• Solo puede usarse **1 vez**.\n"
        msg += "• Expira en **24 horas**.\n"
        msg += "• El nuevo miembro estará asociado a ti.\n"
        
        # Enviar al DM del usuario si fue en el grupo, o responder directamente
        if update.effective_chat.type in ['group', 'supergroup']:
            try:
                await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
            except Exception:
                await _send(context, chat_id, thread_id, f"❌ @{update.effective_user.username}, no pude enviarte el link por mensaje privado. ¡Abre un chat conmigo primero!")
        else:
            await update.message.reply_text(msg, parse_mode='Markdown')
            
    except Exception as e:
        print(f"Error generando invite link: {e}")
        await _send(context, chat_id, thread_id, "❌ Error generando el link de invitación.")

async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /get <id> - Descargar libro con watermark (Anti-Piratería)"""
    if not context.args:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    user_id = update.effective_user.id
    
    try:
        book_id = int(context.args[0])
    except ValueError:
        return
        
    book = await db_manager.get_book_by_id(book_id)
    if not book or not book.get('file_id'):
        await _send(context, chat_id, thread_id, "❌ Libro no encontrado o no disponible.")
        return
        
    status_msg = await _send(context, chat_id, thread_id, "⏳ Preparando archivo seguro...")
    
    try:
        # Descargar el archivo
        import tempfile
        import os
        from pypdf import PdfReader, PdfWriter
        
        tg_file = await context.bot.get_file(book['file_id'])
        ext = book['file_name'].split('.')[-1] if '.' in book['file_name'] else 'pdf'
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}')
        tmp.close()
        path = tmp.name
        
        await tg_file.download_to_drive(path)
        
        # Insertar Watermark si es PDF
        if ext.lower() == 'pdf':
            try:
                reader = PdfReader(path)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                # Agregar metadata secreta con el ID del usuario que lo descargó
                writer.add_metadata({"/AGY-Tracker": str(user_id)})
                
                tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                tmp_out.close()
                with open(tmp_out.name, "wb") as f_out:
                    writer.write(f_out)
                os.replace(tmp_out.name, path)
            except Exception as e:
                print(f"Error watermarking PDF: {e}")
                
        # Enviar al DM del usuario con protect_content=True
        with open(path, 'rb') as f:
            await context.bot.send_document(
                chat_id=user_id,
                document=f,
                filename=book['file_name'],
                caption=book['caption'] or "Aquí tienes tu libro.",
                protect_content=True,
                read_timeout=120,
                write_timeout=120
            )
            
        os.unlink(path)
        
        if status_msg:
            await status_msg.edit_text("✅ Te he enviado el libro por mensaje privado.")
            
    except Exception as e:
        print(f"Error en /get: {e}")
        if status_msg:
            await status_msg.edit_text("❌ Ocurrió un error al procesar el archivo. Si no has iniciado un chat privado conmigo, hazlo primero.")

async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /buscar - Buscar libros en la biblioteca"""
    if not context.args:
        # Sin argumentos
        if update.effective_chat.type == 'private':
            await update.message.reply_text(
                "🔎 **Buscador de la Biblioteca**\n\n"
                "Uso: `/buscar [título o autor]`\n"
                "También puedes buscar por longitud:\n"
                "`/buscar corto` (menos de 200 págs)\n"
                "`/buscar largo` (más de 500 págs)\n\n"
                "Ejemplo: `/buscar Harry Potter`",
                parse_mode='Markdown'
            )
        else:
            chat_id, thread_id = await _delete_cmd(update)
            await _send(context, chat_id, thread_id, "Uso: /buscar [título o autor] o [corto/largo]")
        return
    
    query = ' '.join(context.args)
    if query.lower() == 'corto':
        results = await db_manager.search_library_by_pages('<', 200)
    elif query.lower() == 'largo':
        results = await db_manager.search_library_by_pages('>', 500)
    else:
        results = await db_manager.search_library(query)
    
    if not results:
        msg = f"🔍 No encontré resultados para: *{query}*\n\nIntenta con otro término."
        if update.effective_chat.type == 'private':
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            chat_id, thread_id = await _delete_cmd(update)
            await _send(context, chat_id, thread_id, msg, parse_mode='Markdown')
        return
    
    msg, reply_markup = await build_search_page(query, results, 0)
    
    if update.effective_chat.type == 'private':
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        chat_id, thread_id = await _delete_cmd(update)
        # Si es en grupo, mandar temporal o normal
        bot_msg = await _send(context, chat_id, thread_id, msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
        # Podríamos hacer que se borre a los 5 minutos para no ensuciar
        import asyncio
        async def delete_later(c_id, m_id):
            await asyncio.sleep(300)
            try:
                await context.bot.edit_message_reply_markup(chat_id=c_id, message_id=m_id, reply_markup=None)
            except:
                pass
        if bot_msg:
            asyncio.create_task(delete_later(chat_id, bot_msg.message_id))

async def build_search_page(query: str, results: list, page: int):
    """Genera el texto y teclado para una página de resultados"""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    PER_PAGE = 5
    total = len(results)
    total_pages = (total + PER_PAGE - 1) // PER_PAGE
    
    start = page * PER_PAGE
    end = start + PER_PAGE
    current_results = results[start:end]
    
    msg = f"🔍 **Resultados para:** *{query}*\n"
    msg += f"Encontrados: {total} archivo(s)\n\n"
    
    for i, r in enumerate(current_results, start + 1):
        fname = r.get('file_name', '?')
        topic = r.get('topic_name', '?')
        # Limpiar nombre
        import re
        clean_name = re.sub(r'\.\w+$', '', fname)
        book_id = r.get('id', '')
        
        biblio = "🇪🇸 ESP" if "español" in (topic.lower() if topic else '') else "🇬🇧 ENG"
        msg += f"{i}. {biblio} `{clean_name}`\n"
        if book_id:
            msg += f"   📥 Descargar: `/get {book_id}`\n"
            
    # Recomendación usando el autor del primer resultado
    if current_results and page == 0:
        first_fname = current_results[0].get('file_name', '')
        from utils.book_api import get_book_metadata
        # Obtener metadata rápida
        meta = await get_book_metadata(first_fname)
        if meta and meta.get('author'):
            author = meta['author']
            # Buscar otros libros del autor en nuestra BD
            from database.db_manager import db_manager
            author_results = await db_manager.search_library(author)
            # Filtrar el actual
            other_books = [b for b in author_results if b['id'] != current_results[0]['id']]
            if other_books:
                msg += f"\n💡 *Recomendación:* Si te gusta este autor ({author}), tenemos {len(other_books)} libros más suyos."
        else:
            msg += f"\n💡 *Tip:* Usa los botones de abajo para navegar."
        
    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"search_nav|{query}|{page-1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"search_nav|{query}|{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    return msg, InlineKeyboardMarkup(keyboard) if keyboard else None

async def cmd_directorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /directorio - Índice alfabético de autores"""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    msg = "🗂 **Directorio de Autores**\n\nSelecciona la letra inicial del autor que buscas:"
    
    keyboard = [
        [
            InlineKeyboardButton("A - D", callback_data="dir_range|A|D"),
            InlineKeyboardButton("E - H", callback_data="dir_range|E|H"),
            InlineKeyboardButton("I - L", callback_data="dir_range|I|L")
        ],
        [
            InlineKeyboardButton("M - P", callback_data="dir_range|M|P"),
            InlineKeyboardButton("Q - T", callback_data="dir_range|Q|T"),
            InlineKeyboardButton("U - Z", callback_data="dir_range|U|Z")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.effective_chat.type == 'private':
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        chat_id, thread_id = await _delete_cmd(update)
        bot_msg = await _send(context, chat_id, thread_id, msg, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Borrar menú luego de 5 minutos
        import asyncio
        async def delete_later(c_id, m_id):
            await asyncio.sleep(300)
            try:
                await context.bot.edit_message_reply_markup(chat_id=c_id, message_id=m_id, reply_markup=None)
            except:
                pass
        if bot_msg:
            asyncio.create_task(delete_later(chat_id, bot_msg.message_id))

async def cmd_genero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /genero - Buscar por categoría literaria"""
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) == 0:
        genres = await db_manager.get_all_genres()
        if not genres:
            await _send(context, chat_id, thread_id, "📚 Aún no hay géneros registrados en la biblioteca.")
            return
            
        text = "🏷️ **GÉNEROS LITERARIOS DISPONIBLES**\n\n"
        text += "Usa `/genero <nombre>` para explorar.\n\n"
        
        # Agrupar en texto
        text += ", ".join([f"#{g.replace(' ', '')}" for g in genres])
        await _send(context, chat_id, thread_id, text)
        return
        
    genre_query = " ".join(context.args)
    results = await db_manager.search_library_by_genre(genre_query)
    
    if not results:
        await _send(context, chat_id, thread_id, f"❌ No se encontraron libros para el género '{genre_query}'.")
        return
        
    from handlers.callbacks import send_paginated_results
    await send_paginated_results(update, context, results, f"Resultados para género: {genre_query}")

async def cmd_recomiendame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /recomiendame - Sugerencias basadas en historial"""
    chat_id, thread_id = await _delete_cmd(update)
    user_id = update.effective_user.id
    
    results = await db_manager.get_recommendations(user_id)
    if not results:
        await _send(context, chat_id, thread_id, "❌ No tengo suficientes datos sobre tus gustos. Usa `/pedir` algunas veces para que aprenda qué te gusta.")
        return
        
    from handlers.callbacks import send_paginated_results
    await send_paginated_results(update, context, results, "✨ Libros recomendados para ti:")

async def cmd_masleidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /masleidos - Ver libros con más descargas"""
    chat_id, thread_id = await _delete_cmd(update)
    
    results = await db_manager.get_most_read(limit=10)
    if not results:
        await _send(context, chat_id, thread_id, "📊 Aún no hay registros de descargas.")
        return
        
    text = "🔥 **LOS 10 LIBROS MÁS LEÍDOS**\n\n"
    for i, r in enumerate(results):
        text += f"{i+1}. {r['file_name']} - {r['downloads']} descargas\n"
        
    await _send(context, chat_id, thread_id, text)

async def cmd_diascierre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /diascierre <dias> - Configurar días sin pedidos (0=Lunes, 6=Domingo)"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args:
        current = await db_manager.get_setting('closed_days', '4,6')
        await _send(context, chat_id, thread_id, f"📅 Días de cierre actuales: {current}\n(0=Lunes, 1=Martes... 6=Domingo)\nPara cambiar: `/diascierre 4,6`")
        return
        
    dias = context.args[0]
    await db_manager.set_setting('closed_days', dias, update.effective_user.id)
    
    await _send(context, chat_id, thread_id, f"✅ Días de cierre actualizados a: {dias}")

async def cmd_mispedidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /mispedidos - Ver historial de pedidos propios"""
    chat_id, thread_id = await _delete_cmd(update)
    user_id = update.effective_user.id
    
    reqs = await db_manager.get_user_requests(user_id)
    if not reqs:
        await _send(context, chat_id, thread_id, "📚 Aún no has realizado ningún pedido.")
        return
        
    text = "📖 **TU HISTORIAL DE PEDIDOS**\n\n"
    for r in reqs[:20]: # Mostramos los ultimos 20 por ahora
        status_emoji = "✅" if r['status'] == 'completado' else "❌" if r['status'] == 'cancelado' else "⏳"
        date_str = r['published_date'].split(" ")[0] if r['published_date'] else "Desconocido"
        text += f"{status_emoji} **{r['title']}** - _{r['author']}_ ({date_str})\n"
        
    if len(reqs) > 20:
        text += f"\n_... y {len(reqs) - 20} pedidos más._"
        
    await _send(context, chat_id, thread_id, text)

async def cmd_nopermitir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /nopermitir <titulo> | <motivo>"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    args_text = " ".join(context.args)
    if "|" not in args_text:
        await _send(context, chat_id, thread_id, "⚠️ Uso: `/nopermitir Título del libro | Motivo (ej. Oficialmente prohibido)`")
        return
        
    title, reason = [x.strip() for x in args_text.split("|", 1)]
    await db_manager.add_forbidden_book(title, reason, update.effective_user.id)
    await _send(context, chat_id, thread_id, f"🚫 Libro añadido a la blacklist:\n**{title}**\nMotivo: {reason}")

async def cmd_sipermitir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /sipermitir <titulo>"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    title = " ".join(context.args)
    if not title:
        await _send(context, chat_id, thread_id, "⚠️ Uso: `/sipermitir Título del libro`")
        return
        
    await db_manager.remove_forbidden_book(title)
    await _send(context, chat_id, thread_id, f"✅ Libro removido de la blacklist:\n**{title}**")

async def cmd_bajoperfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /bajoperfil - Activa o desactiva el bloqueo masivo de requests"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    chat_id, thread_id = await _delete_cmd(update)
    current = getattr(config, 'PAUSE_JOIN_REQUESTS', False)
    config.PAUSE_JOIN_REQUESTS = not current
    
    if config.PAUSE_JOIN_REQUESTS:
        await _send(context, chat_id, thread_id, "🛡️ **Modo Bajo Perfil ACTIVADO**\nSe declinarán todas las solicitudes de ingreso nuevas.")
    else:
        await _send(context, chat_id, thread_id, "✅ **Modo Bajo Perfil DESACTIVADO**\nSe procesarán solicitudes normalmente.")

async def cmd_vacaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /vacaciones - Activar/desactivar modo vacaciones"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    current = await db_manager.get_setting('vacation_mode', 'false')
    new_status = 'true' if current == 'false' else 'false'
    
    await db_manager.set_setting('vacation_mode', new_status, update.effective_user.id)
    status_text = "activado (tolerancia ampliada)" if new_status == 'true' else "desactivado (tolerancia normal)"
    await _send(context, chat_id, thread_id, f"🌴 Modo vacaciones **{status_text}**.")

async def cmd_configlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /configlog - Ver log de cambios de configuración"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    logs = await db_manager.get_config_log(15)
    
    if not logs:
        await _send(context, chat_id, thread_id, "No hay cambios de configuración recientes.")
        return
        
    msg = "⚙️ **LOG DE CONFIGURACIÓN**\n\n"
    for log in logs:
        msg += f"**{log['setting_key']}**: `{log['old_value']}` -> `{log['new_value']}`\n"
        msg += f"🗓️ {log['timestamp']} | Por ID: {log['admin_id']}\n\n"
        
    await _send(context, chat_id, thread_id, msg)

async def cmd_miperfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /miperfil - Perfil público del lector"""
    chat_id, thread_id = await _delete_cmd(update)
    user_id = update.effective_user.id
    
    user_data = await db_manager.get_user(user_id)
    if not user_data:
        await _send(context, chat_id, thread_id, "❌ No tengo registros tuyos.")
        return
        
    fav_genre = await db_manager.get_user_favorite_genre(user_id)
    requests = await db_manager.get_user_requests(user_id)
    req_count = len(requests) if requests else 0
    
    # Calcular tiempo
    join_date = datetime.fromisoformat(user_data['join_date'])
    days_active = (datetime.now() - join_date).days
    
    ranks = {0: "Lector", 1: "Colaborador", 2: "Aportador", 3: "Aportador Estrella", 4: "Guardián"}
    user_rank = ranks.get(user_data.get('rank', 0) or 0, "Lector")
    
    msg = f"👤 **PERFIL DE LECTOR**\n"
    msg += f"Usuario: {update.effective_user.first_name}\n"
    msg += f"Rango: **{user_rank}**\n\n"
    msg += f"📚 Libros aportados: {user_data.get('contributions', 0)}\n"
    msg += f"🙏 Libros pedidos: {req_count}\n"
    msg += f"🏷️ Género favorito: {fav_genre}\n"
    msg += f"⏱️ Tiempo en el grupo: {days_active} días\n"
    
    await _send(context, chat_id, thread_id, msg)

async def cmd_misaportes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /misaportes - Ver el historial propio de libros subidos"""
    chat_id, thread_id = await _delete_cmd(update)
    user = update.effective_user
    
    uploads = await db_manager.get_user_uploads(user.id)
    
    if not uploads:
        await _send(context, chat_id, thread_id, "📚 Aún no has aportado ningún libro a la biblioteca. ¡Anímate a compartir!")
        return
        
    msg = f"📚 **TUS APORTES ({len(uploads)})** 📚\n\n"
    
    # Mostrar max 20 para no saturar
    for up in uploads[:20]:
        date_str = up['timestamp'][:10] if up['timestamp'] else "Desconocida"
        msg += f"• `{up['file_name']}` (_{date_str}_)\n"
        
    if len(uploads) > 20:
        msg += f"\n_...y {len(uploads)-20} aportes más._\n"
        
    msg += "\n¡Gracias por contribuir a la comunidad! 💖"
    
    # Send in private if in group, or direct if already in private
    if update.effective_chat.type in ['group', 'supergroup']:
        try:
            await context.bot.send_message(chat_id=user.id, text=msg, parse_mode='Markdown')
            await _send(context, chat_id, thread_id, "✅ Te he enviado tu historial de aportes por mensaje privado.")
        except Exception:
            await _send(context, chat_id, thread_id, "❌ No puedo enviarte mensajes privados. Por favor, iníciame primero enviando /start al bot.")
    else:
        await _send(context, chat_id, thread_id, msg)

async def cmd_estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /estadisticas - Estadísticas del grupo"""
    chat_id, thread_id = await _delete_cmd(update)
    
    stats = await db_manager.get_group_statistics()
    
    msg = f"📊 **ESTADÍSTICAS DEL GRUPO**\n\n"
    msg += f"📚 Total de libros en biblioteca: {stats['total_books']}\n"
    msg += f"✅ Pedidos atendidos (30 días): {stats['requests_month']}\n"
    msg += f"🏷️ Género más popular: {stats['top_genre']}\n"
    msg += f"🏆 Aportador más activo (30 días): {stats['top_contributor']}\n"
    
    await _send(context, chat_id, thread_id, msg)

async def cmd_auditoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /auditoria - Revisar permisos del bot en el grupo (Solo admins)"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    try:
        bot_member = await context.bot.get_chat_member(config.GROUP_ID, context.bot.id)
        
        if bot_member.status != 'administrator':
            await _send(context, chat_id, thread_id, "❌ **Error Crítico:** No soy administrador en el grupo principal.")
            return
            
        perms = bot_member
        
        checks = {
            "Eliminar mensajes": perms.can_delete_messages,
            "Restringir miembros": perms.can_restrict_members,
            "Fijar mensajes": perms.can_pin_messages,
            "Promover miembros": perms.can_promote_members,
            "Invitar usuarios": perms.can_invite_users,
            "Gestionar temas": perms.can_manage_topics,
            "Gestionar chat": perms.can_manage_chat
        }
        
        msg = "🛡️ **AUDITORÍA DE PERMISOS DE SELENE** 🛡️\n\n"
        all_ok = True
        
        for name, has_perm in checks.items():
            if has_perm:
                msg += f"✅ {name}\n"
            else:
                msg += f"❌ {name}\n"
                all_ok = False
                
        msg += "\n"
        if all_ok:
            msg += "✨ **Estado:** Todo correcto. Tengo los permisos necesarios para operar al 100%."
        else:
            msg += "⚠️ **Advertencia:** Me faltan algunos permisos. Funcionalidades como moderación, auto-borrado o pines podrían fallar."
            
        await _send(context, chat_id, thread_id, msg)
    except Exception as e:
        await _send(context, chat_id, thread_id, f"❌ Error ejecutando auditoría: {e}")

async def cmd_simular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /simular - Ver el impacto de una acción moderativa (Admins)"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    if not context.args or len(context.args) < 2:
        await _send(context, chat_id, thread_id, "Uso: `/simular <ban|warn|mute> <user_id>`", parse_mode='Markdown')
        return
        
    action = context.args[0].lower()
    target_id_str = context.args[1]
    
    try:
        target_id = int(target_id_str)
    except:
        await _send(context, chat_id, thread_id, "El user_id debe ser numérico.")
        return
        
    user_data = await db_manager.get_user(target_id)
    if not user_data:
        await _send(context, chat_id, thread_id, f"El usuario {target_id} no existe en la base de datos.")
        return
        
    msg = f"🧪 **SIMULADOR DE CASTIGOS** 🧪\n\n"
    msg += f"**Objetivo:** @{user_data.get('username') or user_data.get('first_name')}\n"
    msg += f"**Acción a simular:** `{action.upper()}`\n\n"
    msg += "⚠️ **EFECTOS ESTIMADOS:**\n"
    
    if action == 'ban':
        msg += "• El usuario será expulsado permanentemente del grupo.\n"
        msg += "• El bot intentará borrar todos sus mensajes recientes.\n"
        msg += "• Su estado en base de datos cambiará a `baneado`.\n"
        msg += "• Perderá inmediatamente el rol Trusted (si lo tiene).\n"
        msg += f"• Se enviará un reporte al canal de alertas sobre el ban de {user_data.get('first_name')}.\n"
    elif action == 'mute':
        msg += "• El usuario será silenciado (no podrá enviar mensajes) por defecto (24h o temporal).\n"
        msg += "• Se añadirá un registro de `mute` en la base de datos.\n"
        msg += f"• Se enviará un DM a {user_data.get('first_name')} avisándole de su muteo.\n"
    elif action == 'warn':
        current_warnings = user_data.get('warnings_count', 0)
        msg += f"• Su contador de advertencias subirá de {current_warnings} a {current_warnings + 1}.\n"
        if current_warnings + 1 >= config.MAX_WARNINGS_BEFORE_BAN:
            msg += "🚨 **¡ALERTA!** Esta advertencia sobrepasaría el límite, resultando en un BAN AUTOMÁTICO.\n"
        else:
            msg += "• Se le enviará un DM advirtiéndole de su infracción.\n"
    else:
        msg += "Acción no reconocida. Usa ban, mute, o warn."
        
    msg += "\n\n_Esta es una simulación. Ningún castigo real fue aplicado._"
    await _send(context, chat_id, thread_id, msg)

async def cmd_sos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /sos - MODO DE EMERGENCIA (Solo admins)"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    # 1. Denegar escritura en todo el grupo
    from telegram import ChatPermissions
    new_perms = ChatPermissions(
        can_send_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False
    )
    
    try:
        await context.bot.set_chat_permissions(
            chat_id=config.GROUP_ID,
            permissions=new_perms
        )
        msg_alerta = "🚨 **¡MODO DE EMERGENCIA ACTIVADO!** 🚨\n\nEl grupo ha sido bloqueado temporalmente por un administrador. Nadie podrá enviar mensajes hasta que se levante la alerta.\n\nPor favor, mantengan la calma."
        if config.TOPIC_GENERAL:
            await context.bot.send_message(chat_id=config.GROUP_ID, message_thread_id=config.TOPIC_GENERAL, text=msg_alerta, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=config.GROUP_ID, text=msg_alerta, parse_mode='Markdown')
            
        await _send(context, chat_id, thread_id, "✅ **Modo SOS activado.** El grupo está en Read-Only.")
    except Exception as e:
        await _send(context, chat_id, thread_id, f"❌ **Error al activar SOS:** No tengo suficientes permisos para cambiar las restricciones globales del chat. ({e})")

async def cmd_exportarbiblioteca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /exportarbiblioteca - Generar y enviar CSV de libros (Admin)"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    await _send(context, chat_id, thread_id, "⏳ Generando exportación de biblioteca...")
    
    items = await db_manager.get_all_library_items()
    if not items:
        await _send(context, chat_id, thread_id, "❌ No hay libros en la biblioteca para exportar.")
        return
        
    import csv
    import os
    from datetime import datetime
    
    filename = f"biblioteca_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Archivo', 'Género', 'Año', 'Páginas', 'Subido Por', 'Fecha Subida']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for item in items:
            username = item.get('username') or item.get('first_name') or 'Desconocido'
            writer.writerow({
                'Archivo': item.get('file_name', ''),
                'Género': item.get('genre', ''),
                'Año': item.get('original_year', ''),
                'Páginas': item.get('page_count', ''),
                'Subido Por': username,
                'Fecha Subida': item.get('timestamp', '')[:10]
            })
            
    try:
        with open(filename, 'rb') as f:
            await context.bot.send_document(
                chat_id=chat_id,
                message_thread_id=thread_id,
                document=f,
                filename=filename,
                caption=f"📚 Exportación de biblioteca ({len(items)} libros)"
            )
    except Exception as e:
        await _send(context, chat_id, thread_id, f"❌ Error enviando archivo: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def cmd_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /pendientes - Mostrar pedidos pendientes agrupados por idioma"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    requests = await db_manager.get_all_pending_requests()
    if not requests:
        await _send(context, chat_id, thread_id, "✅ No hay pedidos pendientes.")
        return
        
    es = []
    en = []
    other = []
    
    for r in requests:
        lang = str(r.get('language', '')).lower()
        if 'español' in lang or 'es' in lang:
            es.append(r)
        elif 'inglés' in lang or 'en' in lang or 'ingles' in lang:
            en.append(r)
        else:
            other.append(r)
            
    msg = f"📋 **PEDIDOS PENDIENTES ({len(requests)})**\n\n"
    
    if es:
        msg += f"🇪🇸 **Español / Ambos** ({len(es)})\n"
        for r in es[:15]:
            msg += f"• *{r['title']}* - {r.get('author', '')}\n"
        if len(es) > 15: msg += f"  _...y {len(es)-15} más_\n"
        msg += "\n"
        
    if en:
        msg += f"🇬🇧 **Inglés** ({len(en)})\n"
        for r in en[:15]:
            msg += f"• *{r['title']}* - {r.get('author', '')}\n"
        if len(en) > 15: msg += f"  _...y {len(en)-15} más_\n"
        msg += "\n"
        
    if other:
        msg += f"❓ **Otros** ({len(other)})\n"
        for r in other[:15]:
            msg += f"• *{r['title']}* - {r.get('author', '')}\n"
        if len(other) > 15: msg += f"  _...y {len(other)-15} más_\n"
        
    await _send(context, chat_id, thread_id, msg)

async def cmd_apelaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /apelaciones - Resumen de apelaciones pendientes"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    chat_id, thread_id = await _delete_cmd(update)
    
    appeals = await db_manager.get_pending_appeals()
    if not appeals:
        await _send(context, chat_id, thread_id, "✅ No hay apelaciones pendientes.")
        return
        
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    
    for ap in appeals[:5]: # Mostrar max 5 para no saturar
        user_data = await db_manager.get_user(ap['user_id'])
        uname = user_data.get('username') or user_data.get('first_name') if user_data else str(ap['user_id'])
        
        msg = f"⚖️ **Apelación #{ap['id']}**\n"
        msg += f"Usuario: @{uname} (ID: {ap['user_id']})\n"
        msg += f"Tipo: {ap['appeal_type']}\n"
        msg += f"Razón: {ap.get('reason', 'N/A')}\n"
        msg += f"Fecha: {ap['created_date'][:10]}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Aprobar", callback_data=f"appeal_approve|{ap['id']}"),
             InlineKeyboardButton("❌ Rechazar", callback_data=f"appeal_reject|{ap['id']}")]
        ])
        
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=msg,
            reply_markup=keyboard
        )
        
    if len(appeals) > 5:
        await _send(context, chat_id, thread_id, f"_...y {len(appeals)-5} apelaciones más pendientes._")

async def cmd_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /hoy - Resumen de actividad diaria"""
    chat_id, thread_id = await _delete_cmd(update)
    
    import aiosqlite
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Miembros nuevos
        async with db.execute("SELECT COUNT(*) FROM users WHERE join_date >= date('now')") as c:
            new_members = (await c.fetchone())[0]
            
        # Libros subidos
        async with db.execute("SELECT COUNT(*) FROM library_backup WHERE timestamp >= date('now')") as c:
            new_books = (await c.fetchone())[0]
            
        # Pedidos realizados
        async with db.execute("SELECT COUNT(*) FROM book_requests WHERE published_date >= date('now')") as c:
            new_requests = (await c.fetchone())[0]
            
        # Warnings emitidos
        async with db.execute("SELECT COUNT(*) FROM warnings WHERE timestamp >= date('now')") as c:
            new_warnings = (await c.fetchone())[0]
            
    msg = "📅 **RESUMEN DE HOY**\n\n"
    msg += f"👥 Nuevos miembros: {new_members}\n"
    msg += f"📚 Libros aportados: {new_books}\n"
    msg += f"🙏 Nuevas peticiones: {new_requests}\n"
    msg += f"⚠️ Advertencias (Warnings): {new_warnings}\n"
    
    await _send(context, chat_id, thread_id, msg)

async def cmd_clasicos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /clasicos - Buscar libros anteriores a 1950"""
    chat_id, thread_id = await _delete_cmd(update)
    
    # Buscar
    results = await db_manager.search_library_by_year('<=', 1950)
    
    if not results:
        msg = "🕰 **Clásicos**\n\nNo se encontraron libros clásicos (anteriores a 1950) en la base de datos."
        if update.effective_chat.type == 'private':
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await _send(context, chat_id, thread_id, msg, parse_mode='Markdown')
        return
        
    msg, reply_markup = await build_search_page("Clásicos (<= 1950)", results, 0)
    
    if update.effective_chat.type == 'private':
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        bot_msg = await _send(context, chat_id, thread_id, msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)

async def cmd_lanzamientos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /lanzamientos - Buscar libros de los últimos 2 años"""
    chat_id, thread_id = await _delete_cmd(update)
    
    from datetime import datetime
    current_year = datetime.now().year
    
    # Buscar
    results = await db_manager.search_library_by_year('>=', current_year - 2)
    
    if not results:
        msg = f"🆕 **Lanzamientos**\n\nNo se encontraron libros recientes (>= {current_year - 2}) en la base de datos."
        if update.effective_chat.type == 'private':
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await _send(context, chat_id, thread_id, msg, parse_mode='Markdown')
        return
        
    msg, reply_markup = await build_search_page(f"Lanzamientos recientes", results, 0)
    
    if update.effective_chat.type == 'private':
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        bot_msg = await _send(context, chat_id, thread_id, msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)

async def cmd_topaportadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /topaportadores - Top 10 usuarios que más aportan libros"""
    chat_id, thread_id = await _delete_cmd(update)
    
    top = await db_manager.get_top_contributors(10)
    
    if not top:
        await _send(context, chat_id, thread_id, "📊 Aún no hay datos de aportes registrados.")
        return
    
    msg = "🏆 **TOP APORTADORES**\n"
    msg += "=" * 30 + "\n\n"
    
    medals = ['🥇', '🥈', '🥉']
    for i, user in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = f"@{user['username']}" if user.get('username') else user.get('first_name', '?')
        count = user.get('contributions', 0)
        
        ranks = {0: "Lector", 1: "Colaborador", 2: "Aportador", 3: "Aportador Estrella", 4: "Guardián"}
        user_rank = ranks.get(user.get('rank', 0) or 0, "Lector")
        
        msg += f"{medal} {name} ({user_rank}) - **{count}** libros\n"
    
    msg += "\n¡Gracias a quienes comparten! 📚"
    
    await _send(context, chat_id, thread_id, msg, parse_mode='Markdown')
