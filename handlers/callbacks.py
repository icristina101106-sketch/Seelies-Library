from telegram import Update
from telegram.ext import ContextTypes
import json
import config
from database.db_manager import db_manager

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar todas las interacciones con botones inline"""
    query = update.callback_query
    
    data = query.data.split('|')
    action = data[0]
    
    # [Fase 5] Panel de Módulos
    if action.startswith("toggle_"):
        if query.from_user.id not in config.ADMIN_IDS:
            return await query.answer("No eres admin", show_alert=True)
            
        from modules import toggles
        if action == "toggle_done":
            await query.answer("Módulos configurados")
            await query.message.delete()
            return
            
        module_name = action.replace("toggle_", "")
        toggles.toggle_module(module_name)
        
        # Actualizar botones
        state = toggles.load_toggles()
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        def btn_text(name, is_on):
            return f"🟢 {name}" if is_on else f"🔴 {name} (Apagado)"
            
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn_text("Moderación y Filtros", state["moderacion"]), callback_data="toggle_moderacion")],
            [InlineKeyboardButton(btn_text("Biblioteca y Subidas", state["biblioteca"]), callback_data="toggle_biblioteca")],
            [InlineKeyboardButton(btn_text("Sistema de Pedidos", state["pedidos"]), callback_data="toggle_pedidos")],
            [InlineKeyboardButton(btn_text("Entradas y Auto-Aceptar", state["entradas"]), callback_data="toggle_entradas")],
            [InlineKeyboardButton("✅ Listo", callback_data="toggle_done")]
        ])
        await query.edit_message_reply_markup(reply_markup=keyboard)
        return
    
    # Manejar callbacks de usuarios comunes
    if action == "rules_accept":
        await query.answer()
        target_user_id = int(data[1])
        chat_id = int(data[2]) if len(data) > 2 else config.GROUP_ID
        if query.from_user.id != target_user_id:
            return

        pending = await db_manager.get_join_request(target_user_id, chat_id)
        if pending and pending.get('status') not in (None, 'pending'):
            await query.edit_message_text(
                text="Esta solicitud ya no está pendiente."
            )
            return

        try:
            await context.bot.approve_chat_join_request(
                chat_id=chat_id,
                user_id=target_user_id
            )
            await db_manager.update_join_request_status(target_user_id, chat_id, 'accepted')
            await db_manager.cancel_pending_tasks('decline_join_request', target_user_id)
            await query.edit_message_text(
                text=query.message.text + "\n\n✅ **Has aceptado las reglas. ¡Bienvenida al grupo!**",
                parse_mode='Markdown',
                reply_markup=None
            )
        except Exception as e:
            print(f"Error aprobando chat join request: {e}")
            err = str(e).lower()
            if 'already' in err or 'not found' in err or 'no pending' in err:
                await db_manager.cancel_pending_tasks('decline_join_request', target_user_id)
                await query.edit_message_text(
                    text="Tu solicitud ya no está pendiente. Si no estás en el grupo, escribe a una administradora."
                )
            else:
                await query.edit_message_text(
                    text="❌ Hubo un error al aprobar tu solicitud. Contacta a una administradora."
                )
        return
        
    if action.startswith('req_'):
        # Ignorar aquí, lo maneja el ConversationHandler
        return
        
    if action == 'oldreq_notfound':
        req_id = int(data[1])
        await query.answer("Marcando como cancelado/no encontrado...")
        await db_manager.mark_request_deleted(req_id)
        
        req_data = await db_manager.get_request(req_id)
        if req_data:
            user_data = await db_manager.get_user(req_data['user_id'])
            if user_data and user_data.get('username'):
                notif = f"📚 ¡Hola @{user_data['username']}!\n\nLamentamos informarte que después de buscar extensamente tu pedido **{req_data['title']}**, no hemos podido encontrarlo en formato digital. El pedido ha sido cerrado."
                await context.bot.send_message(
                    chat_id=config.GROUP_ID,
                    message_thread_id=config.TOPIC_PETICIONES,
                    text=notif
                )
        
        await query.edit_message_text(
            text=query.message.text + "\n\n❌ Marcado como No Encontrado y notificado.",
            parse_mode='Markdown'
        )
        return
        
    if action == 'oldreq_ignore':
        req_id = int(data[1])
        await query.answer("Ignorado.")
        await query.edit_message_text(
            text=query.message.text + "\n\n⏭️ Ignorado por ahora.",
            parse_mode='Markdown'
        )
        return

    if action == 'express_req':
        req_title = data[1] if len(data) > 1 else ""
        await query.answer("Creando pedido...")
        
        # Crear el pedido exprés
        user = query.from_user
        username = user.username or user.first_name
        
        request_id = await db_manager.create_book_request(
            user_id=user.id,
            title=req_title,
            author="No especificado (Exprés)",
            language="Ambos",
            format="Cualquiera",
            request_method='express'
        )
        
        from utils import formatters as formatter
        msg_text = formatter.format_request_published(
            req_title, "No especificado (Exprés)", "Ambos", "Cualquiera", username, 'standalone'
        )
        
        await query.edit_message_text(
            text=msg_text,
            parse_mode='Markdown'
        )
        await db_manager.update_request_message_id(request_id, query.message.message_id)
        return

    if action == 'appeal_approve':
        appeal_id = int(data[1])
        decision = data[2] if len(data) > 2 else 'approve'
        user_id = int(data[3]) if len(data) > 3 else 0
        await query.answer("Procesando apelación...")
        if decision == 'approve':
            await db_manager.update_appeal(appeal_id, 'aprobada', admin_decision=f"Aprobada por {query.from_user.username}")
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ **Apelación Aprobada** por {query.from_user.username}", parse_mode='Markdown')
            # Desbanear
            if user_id:
                await context.bot.unban_chat_member(chat_id=config.GROUP_ID, user_id=user_id, only_if_banned=True)
                await db_manager.update_user_status(user_id, 'nuevo')
        else:
            await db_manager.update_appeal(appeal_id, 'rechazada', admin_decision=f"Rechazada por {query.from_user.username}")
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ **Apelación Rechazada** por {query.from_user.username}", parse_mode='Markdown')
        return
        
    elif action == 'banconfirm':
        user_id = int(data[1])
        reason = data[2] if len(data) > 2 else "Ban manual"
        
        try:
            await context.bot.ban_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
            await db_manager.ban_user(user_id)
            
            await db_manager.log_moderation_action(
                user_id=user_id,
                action_type='ban',
                reason=reason,
                auto_action=False,
                admin_id=query.from_user.id
            )
            
            await db_manager.add_audit_log(
                admin_id=query.from_user.id,
                admin_username=query.from_user.username,
                action_type='ban',
                target_user_id=user_id,
                reason=reason
            )
            
            # Intentar borrar el mensaje infractor si existe
            target_msg_id = context.user_data.get('ban_target_msg_id')
            if target_msg_id:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat.id, message_id=target_msg_id)
                except: pass
                context.user_data.pop('ban_target_msg_id', None)
                
            await query.edit_message_text(text=f"✅ **Usuario baneado con éxito.**\nMotivo: {reason}", parse_mode='Markdown')
            
        except Exception as e:
            await query.edit_message_text(text=f"❌ **Error baneando usuario:** {e}")
        return
            
    elif action == 'bancancel':
        context.user_data.pop('ban_target_msg_id', None)
        await query.edit_message_text(text="❌ **Baneo cancelado.**", parse_mode='Markdown')
        return
        
    if action == 'search_nav':
        search_query = data[1]
        page = int(data[2])
        
        # Obtener resultados
        results = await db_manager.search_library(search_query)
        if not results:
            await query.answer("No hay resultados.", show_alert=True)
            return
            
        from handlers.commands import build_search_page
        msg, reply_markup = await build_search_page(search_query, results, page)
        
        try:
            await query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
            await query.answer()
        except Exception as e:
            await query.answer()
        return

    if action == 'dir_range':
        start_char = data[1]
        end_char = data[2]
        
        authors = await db_manager.get_all_authors()
        
        # Filtrar autores en el rango (ignorando mayus/minus)
        filtered = [a for a in authors if start_char.lower() <= a[0].lower() <= end_char.lower()]
        
        if not filtered:
            await query.answer(f"No hay autores que empiecen con letras de la {start_char} a la {end_char}.", show_alert=True)
            return
            
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = []
        for a in filtered[:30]: # Limitar a 30 por mensaje por límites de Telegram
            # Callback data <= 64 bytes
            cbd = f"dir_author|{a[:50]}"
            keyboard.append([InlineKeyboardButton(a, callback_data=cbd)])
            
        # Botón volver
        keyboard.append([InlineKeyboardButton("🔙 Volver al Índice", callback_data="dir_home")])
        
        msg = f"🗂 **Directorio de Autores [{start_char}-{end_char}]**\n\nSelecciona un autor:"
        await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    if action == 'dir_home':
        from handlers.commands import cmd_directorio
        # Llama a la misma lógica de construcción de msg y keyboard
        # Pero podemos simplemente recrear el menú base aquí para edit_message_text
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
        await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    if action == 'dir_author':
        author = data[1]
        results = await db_manager.get_books_by_author(author)
        if not results:
            await query.answer("No se encontraron libros.", show_alert=True)
            return
            
        from handlers.commands import build_search_page
        msg, reply_markup = await build_search_page(author, results, 0)
        await query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
        return

    if action == 'tour_buscar':
        msg = (
            "🔍 **Buscador de Selene**\n\n"
            "¡Es muy fácil! Solo tienes que escribir `/buscar` seguido del título o autor que deseas.\n\n"
            "Ejemplo:\n`/buscar harry potter`\n\n"
            "Intenta escribirlo ahora mismo en el chat para ver la magia."
        )
        await query.answer("¡Vamos a buscar!", show_alert=False)
        await query.message.reply_text(msg, parse_mode='Markdown')
        return

    if action.startswith('help_'):
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        back_btn = [[InlineKeyboardButton("🔙 Volver", callback_data="help_main")]]
        
        if action == 'help_lector':
            msg = (
                "📖 **Para Lectores**\n\n"
                "• `/buscar [libro/autor]` - Busca en toda la biblioteca.\n"
                "• `/directorio` - Menú interactivo de autores.\n"
                "• `/clasicos` - Libros anteriores a 1950.\n"
                "• `/lanzamientos` - Libros recientes.\n"
                "• `/pedir` - Inicia el asistente para pedir libros faltantes."
            )
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_btn))
            return
            
        elif action == 'help_aportar':
            msg = (
                "🤝 **Para Aportadores**\n\n"
                "Simplemente sube un PDF/EPUB a la biblioteca correspondiente. "
                "Yo extraeré la información de Internet y lo renombraré automáticamente.\n\n"
                "• `/novedades` - Ver últimos añadidos.\n"
                "• `/topaportadores` - Ranking de usuarios.\n"
            )
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_btn))
            return
            
        elif action == 'help_admin':
            if query.from_user.id not in config.ADMIN_IDS:
                await query.answer("Solo administradores.", show_alert=True)
                return
            msg = (
                "🛡️ **Para Admins**\n\n"
                "• `/warn`, `/mute`, `/ban` - Responder para moderar.\n"
                "• `/checkuser`, `/history` - Ver info.\n"
                "• `/config` - Panel de control.\n"
                "• `/modo silencioso` - Apagar respuestas en grupo."
            )
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_btn))
            return
            
        elif action == 'help_main':
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
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=keyboard)
            return

    # A partir de aquí, solo administradores
    if query.from_user.id not in config.ADMIN_IDS:
        await query.answer("Solo administradores pueden usar estos botones.", show_alert=True)
        return
        
    await query.answer()
    
    if action.startswith('panel_'):
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        import config
        back_btn = [[InlineKeyboardButton("🔙 Volver al Panel", callback_data="panel_main")]]
        
        if action == 'panel_main':
            msg = "🎛️ **Panel de Administración**\n\n¿Qué necesitas hacer, Jefe?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Ver Estadísticas", callback_data="panel_stats")],
                [InlineKeyboardButton("💾 Descargar Base de Datos", callback_data="panel_backup")],
                [InlineKeyboardButton("📝 Recordar Comandos", callback_data="panel_cmds")],
                [InlineKeyboardButton("⚙️ Configuración Actual", callback_data="panel_config")],
                [InlineKeyboardButton("📋 Ver Errores (Logs)", callback_data="panel_logs")]
            ])
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=keyboard)
            return
            
        elif action == 'panel_stats':
            stats = await db_manager.get_stats()
            msg = "📊 **ESTADÍSTICAS DEL GRUPO**\n"
            msg += "=" * 35 + "\n\n"
            msg += f"👥 **Usuarios:** {stats['total_users']}\n"
            msg += f"   (Trusted: {stats['trusted_users']}, Silenciados: {stats['muted_users']})\n\n"
            msg += f"📚 **Libros en BD:** {stats['total_books']}\n"
            msg += f"   (Duplicados bloqueados: {stats['total_duplicates']})\n\n"
            msg += f"⚠️ **Sanciones:** {stats['total_warnings']} (Bans: {stats['total_bans']})\n"
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_btn))
            return
            
        elif action == 'panel_backup':
            import os
            from datetime import datetime
            os.makedirs(config.BACKUPS_DIR, exist_ok=True)
            filename = f"selene_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
            dest = os.path.join(config.BACKUPS_DIR, filename)
            import asyncio
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, db_manager.export_database_backup, dest)
            try:
                with open(dest, 'rb') as doc:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=doc,
                        filename=filename,
                        caption="💾 Aquí tienes tu base de datos actualizada."
                    )
                await query.edit_message_text("✅ Base de datos enviada exitosamente.", reply_markup=InlineKeyboardMarkup(back_btn))
            except Exception as e:
                await query.edit_message_text(f"❌ Error al enviar backup: {e}", reply_markup=InlineKeyboardMarkup(back_btn))
            return
            
        elif action == 'panel_cmds':
            help_text = """📚 **COMANDOS DE ADMIN:**

• `/warn` o `/advertir` - Dar advertencia a usuario (respondiendo)
• `/mute` o `/silenciar` - Mutear usuario
• `/unmute` o `/desmutear` - Quitar mute
• `/ban` o `/expulsar` - Expulsar usuario
• `/checkuser` o `/verusuario` - Ver info completa de usuario
• `/history` o `/historial` - Ver historial de sanciones
• `/trust` o `/confiar` - Dar estado trusted
• `/untrust` o `/quitarconfianza` - Quitar trusted
• `/forgive` o `/perdonar` - Perdonar warning
• `/setrisk` - Ajustar nivel de riesgo
• `/checkfotos` o `/revisarfotos` - Revisar fotos de perfil"""
            await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_btn))
            return
            
        elif action == 'panel_config':
            msg = "⚙️ **CONFIGURACIÓN ACTUAL**\n"
            msg += "=" * 35 + "\n\n"
            msg += f"• **Modo:** `{config.MODE}`\n"
            msg += f"• **Modo Prueba:** `{'SÍ' if config.TEST_MODE_ACTIVE else 'NO'}`\n"
            msg += f"• **Modo Silencioso:** `{'SÍ' if config.SILENT_MODE_ACTIVE else 'NO'}`\n"
            msg += f"• **Filtro Palabras:** `{'ACTIVO' if config.WORD_FILTER_ACTIVE else 'INACTIVO'}`\n"
            msg += f"• **Filtro SPAM:** `{'ACTIVO' if config.SPAM_FILTER_ACTIVE else 'INACTIVO'}`\n"
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_btn))
            return
            
        elif action == 'panel_logs':
            import os
            log_file = "seelie.log"
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    last_lines = "".join(lines[-20:])
                msg = f"📋 **Últimas 20 líneas de logs:**\n\n`{last_lines}`"
            else:
                msg = "📋 No hay archivo de logs disponible todavía."
                
            if len(msg) > 4000:
                msg = msg[-4000:]
                
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_btn))
            return
    
    if action.startswith('learn_'):
        case_id = int(data[1])
        decision = action.split('_')[1] # 'ignore', 'warn', 'mute', 'ban'
        
        # Recuperar caso
        case = await db_manager.get_learning_case(case_id)
        if not case:
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ Error: Caso no encontrado.")
            return
            
        # Actualizar base de datos
        await db_manager.update_learning_case(case_id, decision)
        
        ctx_data = json.loads(case['context']) if case['context'] else {}
        user_id = ctx_data.get('user_id')
        
        if user_id and decision != 'ignore':
            user_data = await db_manager.get_user(user_id)
            if user_data:
                from modules.warnings import warnings_module
                from modules.moderation import moderation_module
                
                if decision == 'warn':
                    await warnings_module.issue_warning(
                        user_id=user_id,
                        user_data=user_data,
                        warning_type='caso_ambiguo',
                        severity='baja',
                        context=context,
                        reason="Mensaje inapropiado detectado."
                    )
                elif decision == 'mute':
                    # Aplicamos un mute estándar de nivel 1
                    await warnings_module.issue_warning(
                        user_id=user_id,
                        user_data=user_data,
                        warning_type='caso_ambiguo',
                        severity='media',
                        context=context,
                        reason="Mensaje inapropiado severo detectado."
                    )
                elif decision == 'ban':
                    # Aplicamos un ban
                    await moderation_module.ban_user(
                        user_id=user_id,
                        user_data=user_data,
                        context=context,
                        reason="Mensaje inaceptable (Revisión manual)."
                    )
        
        # Actualizar el mensaje original
        text = query.message.text
        text += f"\n\n✅ **Decisión tomada:** {decision.upper()} por @{query.from_user.username}"
        
        await query.edit_message_text(
            text=text,
            reply_markup=None # Quitar los botones
        )

    elif action.startswith('appeal_'):
        appeal_id = int(data[1])
        decision = action.split('_')[1] # 'approve' or 'reject'
        
        appeal = await db_manager.get_appeal(appeal_id)
        if not appeal:
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ Error: Apelación no encontrada.")
            return
            
        user_id = appeal['user_id']
        
        if decision == 'approve':
            await db_manager.update_appeal(appeal_id, 'aprobada', 'aprobada', f"Aprobada por {query.from_user.username}")
            
            # Notificar al usuario
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ **Tu apelación ha sido APROBADA.**\n\nEl castigo ha sido retirado o perdonado. Por favor, lee nuevamente las reglas para evitar futuras sanciones.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error notificando apelación a {user_id}: {e}")
                
        else: # reject
            await db_manager.update_appeal(appeal_id, 'rechazada', 'rechazada', f"Rechazada por {query.from_user.username}")
            
            # Notificar al usuario
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ **Tu apelación ha sido RECHAZADA.**\n\nLas administradoras han revisado tu caso y decidido mantener la sanción. Esta decisión es final.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error notificando apelación a {user_id}: {e}")
                
        # Actualizar el mensaje original
        text = query.message.text
        estado = "APROBADA ✅" if decision == 'approve' else "RECHAZADA ❌"
        text += f"\n\n**ESTADO:** {estado} (Por: @{query.from_user.username})"
        
        await query.edit_message_text(
            text=text,
            reply_markup=None
        )
