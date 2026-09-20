"""
Módulo de Pedidos de Libros
Sistema interactivo y manual para solicitudes de libros
"""

import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
import config
from database.db_manager import db_manager
from utils.formatters import formatter
from utils.text_analysis import text_analyzer

TIPO_SERIE, TITULO, SEARCH_INTERCEPT, AUTOR, IDIOMA, FORMATO, CONFIRMACION = range(7)


class RequestModule:
    
    # ─── /pedido interactivo ───────────────────────────────────
    
    async def cmd_pedido(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Iniciar pedido interactivo"""
        from modules import toggles
        if not toggles.is_enabled("pedidos"):
            if update.message:
                await update.message.reply_text("⛔ El sistema de pedidos está temporalmente desactivado.")
            return ConversationHandler.END
            
        # Solo funciona en el tema de peticiones
        if not update.message or not update.message.message_thread_id == config.TOPIC_PETICIONES:
            return ConversationHandler.END
            
        # Revisar días cerrados (0=Lunes, 4=Viernes, 6=Domingo)
        closed_days_str = await db_manager.get_setting('closed_days', '4,6')
        closed_days = [int(d) for d in closed_days_str.split(',') if d.strip().isdigit()]
        if datetime.now().weekday() in closed_days:
            await update.message.reply_text(
                "😴 **Día de descanso**\n\nHoy no estamos recibiendo pedidos nuevos para poder procesar los pendientes. ¡Regresa mañana o busca en la biblioteca!",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        context.user_data['request'] = {}
        context.user_data['request_msgs'] = [update.message.message_id]
        bot_msg = await update.message.reply_text(
            "📚 ¿Es una **saga, trilogía, duología** o **standalone** (autoconclusivo)?\n\n"
            "Opciones: `saga`, `trilogía`, `duología`, `standalone`",
            parse_mode='Markdown'
        )
        context.user_data['request_msgs'].append(bot_msg.message_id)
        return TIPO_SERIE
    
    async def recv_tipo_serie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recibir tipo de serie (saga/trilogía/duología/standalone)"""
        tipo = update.message.text.strip().lower()
        
        # Normalizar el tipo
        if tipo in ['trilogia', 'trilogía']:
            context.user_data['request']['tipo'] = 'trilogía'
            hint = "📖 Escribe los **3 títulos** separados por comas o saltos de línea:"
        elif tipo in ['duologia', 'duología', 'duo', 'dúo']:
            context.user_data['request']['tipo'] = 'duología'
            hint = "📖 Escribe los **2 títulos** separados por comas o saltos de línea:"
        elif tipo in ['saga']:
            context.user_data['request']['tipo'] = 'saga'
            hint = "📖 Escribe los **títulos de la saga** separados por comas o saltos de línea:"
        elif tipo in ['standalone', 'autoconclusivo', 'unico', 'único', 'no', 'n/a']:
            context.user_data['request']['tipo'] = 'standalone'
            hint = "📖 ¿Cuál es el **título** del libro?"
        else:
            # Por defecto tratar como standalone
            context.user_data['request']['tipo'] = 'standalone'
            hint = "📖 ¿Cuál es el **título** del libro?"
        
        context.user_data['request_msgs'].append(update.message.message_id)
        bot_msg = await update.message.reply_text(
            f"✅ Tipo: **{context.user_data['request']['tipo']}**\n\n{hint}",
            parse_mode='Markdown'
        )
        context.user_data['request_msgs'].append(bot_msg.message_id)
        return TITULO
    
    async def recv_titulo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recibir título(s)"""
        tipo = context.user_data['request'].get('tipo', 'standalone')
        titulos_texto = update.message.text.strip()
        
        # Guardar los títulos (puede ser uno o varios)
        context.user_data['request']['titulo'] = titulos_texto
        context.user_data['request_msgs'].append(update.message.message_id)
        
        # Comprobar lista negra
        reason = await db_manager.get_forbidden_book_reason(titulos_texto)
        if reason:
            msg = f"🚫 **Libro no permitido**\n\nNo podemos procesar el pedido para **{titulos_texto}**.\nMotivo: _{reason}_"
            bot_msg = await update.message.reply_text(msg, parse_mode='Markdown')
            context.user_data['request_msgs'].append(bot_msg.message_id)
            # Limpiar
            for msg_id in context.user_data.get('request_msgs', []):
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
                except Exception:
                    pass
            context.user_data.pop('request', None)
            context.user_data.pop('request_msgs', None)
            return ConversationHandler.END
            
        # Contar cuántos títulos parece haber (separados por coma o salto de línea)
        import re
        titulos_lista = [t.strip() for t in re.split(r'[,\n]+', titulos_texto) if t.strip()]
        num_titulos = len(titulos_lista)
        
        # Búsqueda Obligatoria si es un solo título (para evitar falsos positivos en sagas)
        if tipo == 'standalone' and num_titulos > 0:
            results = await db_manager.search_library(titulos_lista[0])
            if results:
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                msg = f"🔍 **Búsqueda Automática:** He encontrado esto en la biblioteca para `{titulos_lista[0]}`:\n\n"
                for idx, r in enumerate(results[:3]):
                    msg += f"{idx+1}. {r['file_name']}\n"
                msg += "\n¿Es alguno de estos el libro que buscas?"
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Sí, es uno de esos", callback_data="intercept_yes")],
                    [InlineKeyboardButton("❌ No, continuar pedido", callback_data="intercept_no")]
                ])
                bot_msg = await update.message.reply_text(msg, reply_markup=keyboard, parse_mode='Markdown')
                context.user_data['request_msgs'].append(bot_msg.message_id)
                return SEARCH_INTERCEPT
        
        # Si no hay resultados o no es standalone, continuar flujo normal
        return await self._ask_author(update, context, tipo, num_titulos)
        
    async def _ask_author(self, update_or_query, context, tipo, num_titulos):
        """Función auxiliar para pedir el autor"""
        if tipo == 'standalone':
            confirm = "✅ Título recibido"
        elif tipo == 'duología':
            confirm = f"✅ **Duología** - {num_titulos} títulos recibidos"
        elif tipo == 'trilogía':
            confirm = f"✅ **Trilogía** - {num_titulos} títulos recibidos"
        else:
            confirm = f"✅ **Saga** - {num_titulos} títulos recibidos"
        
        msg = f"{confirm}\n\n📝 ¿Quién es el **autor**?"
        
        if hasattr(update_or_query, 'message') and update_or_query.message:
            bot_msg = await update_or_query.message.reply_text(msg, parse_mode='Markdown')
        else:
            bot_msg = await context.bot.send_message(
                chat_id=update_or_query.message.chat.id,
                message_thread_id=update_or_query.message.message_thread_id,
                text=msg,
                parse_mode='Markdown'
            )
            
        context.user_data['request_msgs'].append(bot_msg.message_id)
        return AUTOR

    async def handle_search_intercept(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar respuesta a búsqueda obligatoria"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'intercept_yes':
            # Cancelar pedido
            for msg_id in context.user_data.get('request_msgs', []):
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
                except Exception:
                    pass
            context.user_data.pop('request', None)
            context.user_data.pop('request_msgs', None)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                message_thread_id=query.message.message_thread_id,
                text="✅ ¡Genial! Usa `/buscar` para encontrar el libro en la biblioteca. Pedido cancelado.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
            
        elif query.data == 'intercept_no':
            # Continuar pidiendo el autor
            try:
                await query.message.delete()
            except: pass
            return await self._ask_author(query, context, 'standalone', 1)

    async def recv_autor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recibir autor"""
        context.user_data['request']['autor'] = update.message.text.strip()
        context.user_data['request_msgs'].append(update.message.message_id)
        bot_msg = await update.message.reply_text(
            "🌐 ¿En qué **idioma**? (Español / Inglés / Ambos)",
            parse_mode='Markdown'
        )
        context.user_data['request_msgs'].append(bot_msg.message_id)
        return IDIOMA
    
    async def recv_idioma(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recibir idioma"""
        context.user_data['request']['idioma'] = update.message.text.strip()
        context.user_data['request_msgs'].append(update.message.message_id)
        bot_msg = await update.message.reply_text(
            "📄 ¿En qué **formato**? (PDF / EPUB / Ambos)",
            parse_mode='Markdown'
        )
        context.user_data['request_msgs'].append(bot_msg.message_id)
        return FORMATO
    
    async def recv_formato(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recibir formato y verificar si existe en la biblioteca antes de publicar"""
        context.user_data['request']['formato'] = update.message.text.strip()
        context.user_data['request_msgs'].append(update.message.message_id)
        
        # Buscar en biblioteca si ya existe
        titulo = context.user_data['request']['titulo']
        results = await db_manager.search_library(titulo)
        
        if results:
            # Encontramos resultados, advertir
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            msg = f"🔍 **Posible libro repetido**\n\nHe encontrado {len(results)} archivo(s) similar(es) en la biblioteca:\n\n"
            for i, r in enumerate(results[:3], 1):
                fname = r.get('file_name', '?')
                chat_id_str = str(r.get('chat_id', ''))
                if chat_id_str.startswith('-100'): chat_id_str = chat_id_str[4:]
                msg_id = r.get('message_id', '')
                link = f"https://t.me/c/{chat_id_str}/{msg_id}" if chat_id_str and msg_id else ""
                if link:
                    msg += f"- [{fname}]({link})\n"
                else:
                    msg += f"- `{fname}`\n"
            
            msg += "\n¿Estás seguro de que quieres realizar este pedido?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Sí, pedir de todos modos", callback_data="req_confirm")],
                [InlineKeyboardButton("❌ Cancelar pedido", callback_data="req_cancel")]
            ])
            
            bot_msg = await update.message.reply_text(
                msg, 
                reply_markup=keyboard, 
                parse_mode='Markdown', 
                disable_web_page_preview=True
            )
            context.user_data['request_msgs'].append(bot_msg.message_id)
            return CONFIRMACION
            
        else:
            # Autocorrector con Google Books
            from utils.book_api import get_book_metadata
            meta = await get_book_metadata(titulo)
            if meta and meta.get('title'):
                official_title = meta['title']
                official_author = meta.get('author', context.user_data['request']['autor'])
                
                # Simple heurística de diferencia (podemos usar difflib o simple len check)
                import difflib
                similarity = difflib.SequenceMatcher(None, titulo.lower(), official_title.lower()).ratio()
                
                if similarity < 0.9 and similarity > 0.4:
                    # Sugerir corrección
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    # Guardamos la sugerencia en context
                    context.user_data['suggestion'] = {
                        'titulo': official_title,
                        'autor': official_author
                    }
                    
                    msg = f"🤔 **Sugerencia de corrección**\n\n"
                    msg += f"Parece que el título o autor podrían estar mal escritos. Según la base de datos oficial, el libro es:\n\n"
                    msg += f"📖 **{official_title}** de _{official_author}_\n\n"
                    msg += f"¿Quieres corregirlo antes de publicar?"
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("✨ Sí, corregir automáticamente", callback_data="req_correct")],
                        [InlineKeyboardButton("⏭️ No, publicar como lo escribí", callback_data="req_confirm")]
                    ])
                    
                    bot_msg = await update.message.reply_text(
                        msg, 
                        reply_markup=keyboard, 
                        parse_mode='Markdown'
                    )
                    context.user_data['request_msgs'].append(bot_msg.message_id)
                    return CONFIRMACION
                    
            return await self._publish_request(update, context)

    async def handle_req_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar la confirmación inline del pedido repetido o sugerencia"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "req_confirm":
            return await self._publish_request(update, context)
        elif query.data == "req_correct":
            # Aplicar sugerencia
            sug = context.user_data.get('suggestion')
            if sug:
                context.user_data['request']['titulo'] = sug['titulo']
                context.user_data['request']['autor'] = sug['autor']
            return await self._publish_request(update, context)
        elif query.data == "req_cancel":
            return await self.cancel_pedido(update, context)
            
    async def _publish_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Publicar pedido en el grupo"""
        data = context.user_data['request']
        user = update.effective_user
        username = user.username or user.first_name
        
        # Verificar si hay un pedido similar en pending
        pending_requests = await db_manager.get_pending_requests_matching(data['titulo'])
        if pending_requests:
            # Hay pedido pendiente similar
            existing_req = pending_requests[0]
            if existing_req['user_id'] != user.id:
                await db_manager.add_to_waitlist(existing_req['id'], user.id)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    message_thread_id=config.TOPIC_PETICIONES,
                    text=f"📚 @{username}, alguien más ya había pedido **{data['titulo']}**. ¡Te he añadido a la lista de espera! Te avisaré por privado cuando el libro sea subido al grupo."
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    message_thread_id=config.TOPIC_PETICIONES,
                    text=f"⚠️ @{username}, ya habías pedido este libro y está en la lista de espera."
                )
            # Limpiar
            for msg_id in context.user_data.get('request_msgs', []):
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
                except Exception:
                    pass
            context.user_data.pop('request', None)
            context.user_data.pop('request_msgs', None)
            return ConversationHandler.END
            
        # Guardar en BD (todos los títulos en el campo title)
        request_id = await db_manager.create_book_request(
            user_id=user.id,
            title=data['titulo'],  # Puede contener múltiples títulos
            author=data['autor'],
            language=data['idioma'],
            format=data['formato'],
            request_method='interactivo'
        )
        
        # Publicar pedido formateado
        tipo = data.get('tipo', 'standalone')
        msg_text = formatter.format_request_published(
            data['titulo'], data['autor'], data['idioma'], data['formato'], username, tipo
        )
        
        # Obtener chat id correcto (podría venir de message o de callback_query)
        chat_id = update.effective_chat.id
        
        published = await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=config.TOPIC_PETICIONES,
            text=msg_text
        )
        
        await db_manager.update_request_message_id(request_id, published.message_id)
        
        # Borrar todos los mensajes de la conversación (preguntas + respuestas)
        for msg_id in context.user_data.get('request_msgs', []):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except:
                pass
        
        context.user_data.pop('request', None)
        context.user_data.pop('request_msgs', None)
        return ConversationHandler.END
    
    async def cancel_pedido(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancelar pedido en curso"""
        context.user_data.pop('request', None)
        await update.message.reply_text("❌ Pedido cancelado.")
        return ConversationHandler.END
    
    # ─── Detección manual de pedidos ───────────────────────────
    
    async def check_manual_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detectar y validar pedidos escritos manualmente en Peticiones"""
        message = update.message
        if not message or not message.text:
            return
        
        # Solo en tema de peticiones
        if message.message_thread_id != config.TOPIC_PETICIONES:
            return
        
        # Ignorar admin
        if message.from_user.id == config.ADMIN_ID:
            return
        
        text = message.text.strip()
        
        # Intentar extraer datos del pedido
        data = text_analyzer.extract_request_data(text)
        is_valid, missing = text_analyzer.validate_request_format(data)
        
        if is_valid:
            # Formato correcto → publicar formateado
            user = message.from_user
            username = user.username or user.first_name
            
            request_id = await db_manager.create_book_request(
                user_id=user.id,
                title=data['titulo'],
                author=data['autor'],
                language=data['idioma'],
                format=data['formato'],
                request_method='manual'
            )
            
            msg_text = formatter.format_request_published(
                data['titulo'], data['autor'], data['idioma'], data['formato'], username, 'standalone'
            )
            
            # Borrar mensaje original y publicar formateado
            try:
                await message.delete()
            except:
                pass
            
            published = await context.bot.send_message(
                chat_id=message.chat_id,
                message_thread_id=config.TOPIC_PETICIONES,
                text=msg_text
            )
            
            await db_manager.update_request_message_id(request_id, published.message_id)
        else:
            # Evaluar si podría ser un pedido exprés (solo un título o texto corto sin formato)
            if len(text.split('\n')) <= 2 and len(text) < 100:
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Hacer pedido formal", callback_data=f"express_req|{text[:40]}")]
                ])
                warning_msg = (
                    f"🤔 @{message.from_user.username or message.from_user.first_name}, parece que intentas pedir un libro.\n\n"
                    f"¿Quieres iniciar un pedido formal para: **{text}**?"
                )
                try:
                    await message.delete()
                except:
                    pass
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    message_thread_id=config.TOPIC_PETICIONES,
                    text=warning_msg,
                    reply_markup=keyboard
                )
                return
            
            # Formato incorrecto -> warning + sugerencia
            missing_str = ', '.join(missing)
            
            warning_msg = (
                f"⚠️ @{message.from_user.username or message.from_user.first_name}, "
                f"a tu pedido le falta: **{missing_str}**\n\n"
                f"💡 Usa /pedido para que te guíe paso a paso y evitar warnings.\n\n"
                f"El formato correcto es:\n"
                f"```\n"
                f"Título: nombre del libro\n"
                f"Autor: nombre del autor\n"
                f"Idioma: Español/Inglés\n"
                f"Formato: PDF/EPUB/Ambos\n"
                f"```"
            )
            
            # Borrar mensaje incorrecto
            try:
                await message.delete()
            except:
                pass
            
            await context.bot.send_message(
                chat_id=message.chat_id,
                message_thread_id=config.TOPIC_PETICIONES,
                text=warning_msg,
                parse_mode='Markdown'
            )
            
            # Registrar warning
            await db_manager.add_request_warning(
                request_id=0,
                user_id=message.from_user.id,
                warning_type='incompleto',
                message=f"Campos faltantes: {missing_str}"
            )
    
    # ─── Comandos admin ────────────────────────────────────────
    
    async def cmd_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Marcar pedido como atendido (responder al mensaje del pedido)"""
        if update.effective_user.id not in config.ADMIN_IDS:
            return
        
        chat_id = update.effective_chat.id
        thread_id = update.message.message_thread_id
        reply_msg = update.message.reply_to_message
        
        # Borrar el mensaje del comando
        try:
            await update.message.delete()
        except:
            pass
        
        if not reply_msg:
            await context.bot.send_message(
                chat_id=chat_id, message_thread_id=thread_id,
                text="❌ Responde al mensaje del pedido que quieres marcar como atendido."
            )
            return
        
        request_data = await db_manager.get_request_by_message_id(reply_msg.message_id)
        
        if not request_data:
            await context.bot.send_message(
                chat_id=chat_id, message_thread_id=thread_id,
                text="❌ No se encontró un pedido asociado a ese mensaje."
            )
            return
        
        # Marcar como atendido
        auto_delete_time = await db_manager.mark_request_completed(request_data['id'])
        
        # Notificar al usuario principal
        user_data = await db_manager.get_user(request_data['user_id'])
        if user_data and user_data['username']:
            notification = formatter.format_request_ready_notification(user_data['username'])
            await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=config.TOPIC_PETICIONES,
                text=notification
            )
            
        # Notificar a usuarios en lista de espera
        waitlist_users = await db_manager.get_waitlist_users(request_data['id'])
        for w_user_id in waitlist_users:
            w_user_data = await db_manager.get_user(w_user_id)
            if w_user_data and w_user_data.get('username'):
                notif = f"📚 ¡Hola @{w_user_data['username']}! El libro **{request_data['title']}** que estabas esperando ya ha sido subido a la biblioteca. Puedes ir a buscarlo."
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=config.TOPIC_PETICIONES,
                    text=notif
                )
        
        await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id,
            text=f"✅ Pedido #{request_data['id']} marcado como atendido.\n"
                 f"Se eliminará automáticamente en {config.REQUEST_AUTO_DELETE_HOURS}h."
        )
    
    async def cmd_pedidos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Listar pedidos pendientes"""
        if update.effective_user.id not in config.ADMIN_IDS:
            return
        
        chat_id = update.effective_chat.id
        thread_id = update.message.message_thread_id
        
        # Borrar el mensaje del comando
        try:
            await update.message.delete()
        except:
            pass
        
        pending = await self._get_pending_requests()
        
        if not pending:
            await context.bot.send_message(
                chat_id=chat_id, message_thread_id=thread_id,
                text="📭 No hay pedidos pendientes."
            )
            return
        
        msg = f"📋 **PEDIDOS PENDIENTES** ({len(pending)})\n"
        msg += "=" * 35 + "\n\n"
        
        for req in pending:
            user = await db_manager.get_user(req['user_id'])
            username = f"@{user['username']}" if user and user['username'] else f"ID:{req['user_id']}"
            msg += f"#{req['id']} — {req['title']}\n"
            msg += f"   ✍️ {req['author']} | 🌐 {req['language']} | 📄 {req['format']}\n"
            msg += f"   👤 {username}\n\n"
        
        await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id,
            text=msg, parse_mode='Markdown'
        )
    
    async def _get_pending_requests(self):
        """Obtener pedidos pendientes de la BD"""
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM book_requests 
                WHERE status = 'pendiente' AND deleted = 0
                ORDER BY published_date DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    def get_conversation_handler(self):
        """Crear ConversationHandler para /pedido"""
        return ConversationHandler(
            entry_points=[CommandHandler('pedido', self.cmd_pedido)],
            states={
                TIPO_SERIE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.recv_tipo_serie)],
                TITULO: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.recv_titulo)],
                SEARCH_INTERCEPT: [CallbackQueryHandler(self.handle_search_intercept, pattern='^intercept_')],
                AUTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.recv_autor)],
                IDIOMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.recv_idioma)],
                FORMATO: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.recv_formato)],
                CONFIRMACION: [CallbackQueryHandler(self.handle_req_callback, pattern='^req_')],
            },
            fallbacks=[CommandHandler('cancelar', self.cancel_pedido)],
            per_user=True,
            per_chat=True
        )


# Instancia global
request_module = RequestModule()
