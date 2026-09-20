"""
Módulo de Moderación Automática
Detecta infracciones y aplica acciones
"""

from telegram import Update, Message
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from collections import defaultdict
import config
from database.db_manager import db_manager
from utils.text_analysis import text_analyzer
from utils.formatters import formatter

# Almacenamiento temporal para detección de flood
user_message_times = defaultdict(list)
user_last_messages = defaultdict(str)
user_repeat_count = defaultdict(int)

class ModerationModule:
    
    @staticmethod
    async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """
        Verificar mensaje y aplicar moderación si es necesario
        Retorna: True si el mensaje fue moderado, False si está ok
        """
        message = update.message
        if not message:
            return False
        
        user_id = message.from_user.id
        text = message.text or message.caption or ""
        
        # Obtener palabras prohibidas
        forbidden_words = await db_manager.get_forbidden_words()
        
        # 1. Verificar links
        if text_analyzer.has_links(text):
            # Los admins pueden enviar links (excepto en modo prueba)
            if user_id != config.ADMIN_ID or config.TEST_MODE_ACTIVE:
                await ModerationModule._handle_link(message, user_data, context)
                return True
        
        # 2. Verificar invitaciones a grupos
        if text_analyzer.has_invites(text):
            if user_id != config.ADMIN_ID or config.TEST_MODE_ACTIVE:
                await ModerationModule._handle_invite(message, user_data, context)
                return True
        
        # 3. Verificar palabras prohibidas
        forbidden_check = text_analyzer.check_forbidden_words(text, forbidden_words)
        if forbidden_check:
            word, severity, action = forbidden_check
            await ModerationModule._handle_forbidden_word(message, user_data, word, severity, action, context)
            return True
        
        # 4. Verificar flood
        if await ModerationModule._check_flood(user_id, message, user_data, context):
            return True
        
        # 5. Verificar mensajes repetidos
        if await ModerationModule._check_repeated_message(user_id, text, message, user_data, context):
            return True
        
        # 6. Verificar archivos sospechosos
        if message.document:
            if await ModerationModule._check_suspicious_file(message, user_data, context):
                return True
        
        # 7. Verificar reenvíos masivos
        if message.forward_date:
            if await ModerationModule._check_forward_spam(user_id, message, user_data, context):
                return True
        
        # 8. Detectar tono agresivo (solo alerta, no acción automática)
        if text_analyzer.detect_aggressive_tone(text):
            if config.LEARNING_ENABLED and config.REQUIRE_ADMIN_DECISION_FOR_AMBIGUOUS:
                await ModerationModule._alert_ambiguous_case(message, user_data, "tono_agresivo", context)
                
        # 9. Detectar similitud con mensajes de usuarios baneados (Spam Patterns)
        if len(text) > 20:
            banned_texts = await db_manager.get_banned_user_messages()
            import difflib
            for btext in banned_texts:
                sim = difflib.SequenceMatcher(None, text.lower(), btext).ratio()
                if sim > 0.85:
                    await ModerationModule._handle_banned_similarity(message, user_data, context, btext)
                    return True
                    
        # 10. Detección de bots (Flood tras registro)
        try:
            from datetime import datetime
            join_date = datetime.fromisoformat(user_data['join_date'])
            minutes_since_join = (datetime.now() - join_date).total_seconds() / 60
            if minutes_since_join < 3 and user_data.get('message_count', 0) > 5:
                await ModerationModule._handle_bot_flood(message, user_data, context)
                return True
        except:
            pass
        
        return False

    @staticmethod
    async def _handle_bot_flood(message: Message, user_data: dict, context):
        """Manejar flood de bot apenas entra"""
        user_id = message.from_user.id
        from database.db_manager import db_manager
        
        await db_manager.add_warning(
            user_id,
            warning_type='bot_flood',
            severity='critica',
            message_text="[Flood masivo post-registro]"
        )
        
        try:
            await message.delete()
        except: pass
        
        await context.bot.send_message(
            chat_id=config.ALERT_GROUP_ID,
            message_thread_id=config.ALERT_TOPIC_ID if hasattr(config, 'ALERT_TOPIC_ID') else None,
            text=f"🤖 **POSIBLE BOT DETECTADO** 🤖\n\nEl usuario @{message.from_user.username or message.from_user.first_name} (ID: {user_id}) ha enviado más de 5 mensajes en menos de 3 minutos tras unirse.\n\nEl último mensaje ha sido borrado.",
            parse_mode='Markdown'
        )

    @staticmethod
    async def _handle_banned_similarity(message: Message, user_data: dict, context, matched_text: str):
        """Manejar mensaje similar a uno de usuario baneado"""
        user_id = message.from_user.id
        from database.db_manager import db_manager
        
        await db_manager.add_warning(
            user_id,
            warning_type='spam_pattern',
            severity='alta',
            message_text=message.text
        )
        
        try:
            await message.delete()
        except:
            pass
            
        await context.bot.send_message(
            chat_id=config.ALERT_GROUP_ID,
            message_thread_id=config.ALERT_TOPIC_ID if hasattr(config, 'ALERT_TOPIC_ID') else None,
            text=f"🚨 **ALERTA PREVENTIVA** 🚨\n\nEl usuario @{message.from_user.username or message.from_user.first_name} (ID: {user_id}) envió un mensaje muy similar (patrón de spam) al de un usuario previamente baneado.\n\nEl mensaje ha sido eliminado preventivamente.\n\nMensaje original:\n`{message.text}`",
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def _handle_link(message: Message, user_data: dict, context: ContextTypes.DEFAULT_TYPE):
        """Manejar detección de link"""
        user_id = message.from_user.id
        
        # Borrar mensaje
        if not config.TEST_MODE_ACTIVE:
            await message.delete()
        
        # Agregar warning
        await db_manager.add_warning(
            user_id=user_id,
            warning_type='link',
            severity='media',
            message_text=message.text or message.caption,
            message_id=message.message_id,
            chat_id=message.chat_id,
            topic_id=message.message_thread_id,
            action_taken='delete+warning'
        )
        
        # Agregar riesgo
        risk_points = config.RISK_POINTS['link']
        if user_data['status'] == 'nuevo':
            risk_points += config.RISK_POINTS['new_user_link']
        
        await db_manager.add_risk_event(
            user_id=user_id,
            event_type='link',
            risk_points=risk_points,
            description='Envió link no permitido'
        )
        
        # Log acción
        await db_manager.log_moderation_action(
            user_id=user_id,
            action_type='delete',
            reason='link',
            message_deleted=message.text or message.caption,
            message_id=message.message_id,
            chat_id=message.chat_id,
            topic_id=message.message_thread_id
        )
        
        # Enviar mensaje en tema de administración
        warning_msg = formatter.format_warning_message('link', 'media')
        if config.TEST_MODE_ACTIVE:
            warning_msg = formatter.format_test_mode_message(warning_msg)
        
        if not config.SILENT_MODE_ACTIVE:
            await context.bot.send_message(
                chat_id=config.GROUP_ID,
                message_thread_id=config.TOPIC_ADMINISTRACION,
                text=warning_msg
            )
        
        # Aplicar castigo progresivo
        from modules.warnings import warnings_module
        await warnings_module.apply_progressive_punishment(user_id, user_data, context)
        
        # Enviar alerta
        await ModerationModule._send_alert(user_id, message.from_user.username, user_data, 'link', message.text or message.caption, 'delete+warning', context)
    
    @staticmethod
    async def _handle_invite(message: Message, user_data: dict, context: ContextTypes.DEFAULT_TYPE):
        """Manejar invitación a grupo"""
        user_id = message.from_user.id
        
        # Borrar mensaje
        if not config.TEST_MODE_ACTIVE:
            await message.delete()
        
        # Agregar warning
        await db_manager.add_warning(
            user_id=user_id,
            warning_type='invitacion',
            severity='grave',
            message_text=message.text,
            message_id=message.message_id,
            chat_id=message.chat_id,
            topic_id=message.message_thread_id,
            action_taken='delete+warning'
        )
        
        # Agregar riesgo alto
        await db_manager.add_risk_event(
            user_id=user_id,
            event_type='invitacion_grupo',
            risk_points=config.RISK_POINTS['invitacion_grupo'],
            description='Envió invitación a otro grupo'
        )
        
        # Log acción
        await db_manager.log_moderation_action(
            user_id=user_id,
            action_type='delete',
            reason='invitacion',
            message_deleted=message.text,
            message_id=message.message_id,
            chat_id=message.chat_id,
            topic_id=message.message_thread_id
        )
        
        # Mensaje
        warning_msg = formatter.format_warning_message('invitacion', 'grave')
        if not config.SILENT_MODE_ACTIVE:
            await context.bot.send_message(
                chat_id=config.GROUP_ID,
                message_thread_id=config.TOPIC_ADMINISTRACION,
                text=warning_msg
            )
        
        # Castigo progresivo
        from modules.warnings import warnings_module
        await warnings_module.apply_progressive_punishment(user_id, user_data, context)
        
        # Alerta
        await ModerationModule._send_alert(user_id, message.from_user.username, user_data, 'invitacion_grupo', message.text, 'delete+warning', context)
    
    @staticmethod
    async def _handle_forbidden_word(message: Message, user_data: dict, word: str, severity: str, action: str, context: ContextTypes.DEFAULT_TYPE):
        """Manejar palabra prohibida"""
        user_id = message.from_user.id
        
        # Borrar mensaje
        if not config.TEST_MODE_ACTIVE:
            await message.delete()
        
        # Agregar warning
        await db_manager.add_warning(
            user_id=user_id,
            warning_type=f'palabra_{severity}',
            severity=severity,
            message_text=message.text or message.caption,
            message_id=message.message_id,
            chat_id=message.chat_id,
            topic_id=message.message_thread_id,
            action_taken=action
        )
        
        # Agregar riesgo
        risk_points = config.RISK_POINTS[f'palabra_{severity}']
        await db_manager.add_risk_event(
            user_id=user_id,
            event_type=f'palabra_{severity}',
            risk_points=risk_points,
            description=f'Usó palabra prohibida: {word}'
        )
        
        # Log acción
        await db_manager.log_moderation_action(
            user_id=user_id,
            action_type='delete',
            reason=f'palabra_{severity}',
            message_deleted=message.text or message.caption,
            message_id=message.message_id,
            chat_id=message.chat_id,
            topic_id=message.message_thread_id
        )
        
        # Aplicar acción según severidad
        if severity == 'grave' and action == 'ban':
            # Ban directo
            if not config.TEST_MODE_ACTIVE:
                await context.bot.ban_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
                await db_manager.ban_user(user_id)
            
            ban_msg = formatter.format_ban_message()
            if config.TEST_MODE_ACTIVE:
                ban_msg = formatter.format_test_mode_message(ban_msg)
            
            if not config.SILENT_MODE_ACTIVE:
                await context.bot.send_message(
                    chat_id=config.GROUP_ID,
                    message_thread_id=config.TOPIC_ADMINISTRACION,
                    text=ban_msg
                )
            
            await ModerationModule._send_alert(user_id, message.from_user.username, user_data, f'palabra_grave: {word}', message.text, 'BAN', context)
        
        elif severity == 'media' and action == 'mute_1h':
            # Mute 1 hora
            if not config.TEST_MODE_ACTIVE:
                until_date = datetime.now() + timedelta(minutes=config.MUTE_DURATION_1)
                await context.bot.restrict_chat_member(
                    chat_id=config.GROUP_ID,
                    user_id=user_id,
                    permissions={"can_send_messages": False},
                    until_date=until_date
                )
            
            mute_msg = formatter.format_mute_message(config.MUTE_DURATION_1)
            if config.TEST_MODE_ACTIVE:
                mute_msg = formatter.format_test_mode_message(mute_msg)
            
            if not config.SILENT_MODE_ACTIVE:
                await context.bot.send_message(
                    chat_id=config.GROUP_ID,
                    message_thread_id=config.TOPIC_ADMINISTRACION,
                    text=mute_msg
                )
            
            await ModerationModule._send_alert(user_id, message.from_user.username, user_data, f'palabra_media: {word}', message.text, 'mute_1h', context)
        
        else:
            # Solo warning
            warning_msg = formatter.format_warning_message(f'palabra_{severity}', severity)
            if config.TEST_MODE_ACTIVE:
                warning_msg = formatter.format_test_mode_message(warning_msg)
            
            if not config.SILENT_MODE_ACTIVE:
                await context.bot.send_message(
                    chat_id=config.GROUP_ID,
                    message_thread_id=config.TOPIC_ADMINISTRACION,
                    text=warning_msg
                )
            
            # Castigo progresivo
            from modules.warnings import warnings_module
            await warnings_module.apply_progressive_punishment(user_id, user_data, context)
            
            await ModerationModule._send_alert(user_id, message.from_user.username, user_data, f'palabra_{severity}: {word}', message.text, 'warning', context)
    
    @staticmethod
    async def _check_flood(user_id: int, message: Message, user_data: dict, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Verificar flood de mensajes"""
        # Ignorar mensajes en biblioteca y peticiones (no son flood, son uso normal)
        if message.message_thread_id in [config.TOPIC_BIBLIOTECA_ESP, config.TOPIC_BIBLIOTECA_ING, config.TOPIC_PETICIONES]:
            return False
        
        current_time = datetime.now()
        
        # Limpiar mensajes antiguos
        user_message_times[user_id] = [
            t for t in user_message_times[user_id]
            if (current_time - t).total_seconds() < config.FLOOD_TIME_SECONDS
        ]
        
        # Agregar mensaje actual
        user_message_times[user_id].append(current_time)
        
        # Verificar si excede el límite
        if len(user_message_times[user_id]) >= config.FLOOD_MESSAGE_COUNT:
            # Flood detectado
            await db_manager.add_warning(
                user_id=user_id,
                warning_type='flood',
                severity='media',
                message_text=f"Flood: {len(user_message_times[user_id])} mensajes en {config.FLOOD_TIME_SECONDS}s",
                message_id=message.message_id,
                chat_id=message.chat_id,
                topic_id=message.message_thread_id,
                action_taken='warning'
            )
            
            await db_manager.add_risk_event(
                user_id=user_id,
                event_type='flood',
                risk_points=config.RISK_POINTS['flood'],
                description='Flood de mensajes'
            )
            
            # Verificar si es la segunda advertencia de flood en poco tiempo
            warnings_count = await db_manager.get_warning_count(user_id)
            recent_flood_warnings = await db_manager.get_user_warnings(user_id, limit=5)
            flood_warnings_recent = [w for w in recent_flood_warnings if w['warning_type'] == 'flood']
            
            if len(flood_warnings_recent) >= config.FLOOD_WARNINGS_BEFORE_BAN:
                # Ban directo por flood reiterado
                if not config.TEST_MODE_ACTIVE:
                    await context.bot.ban_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
                    await db_manager.ban_user(user_id)
                
                ban_msg = "Usuario baneado por flood reiterado."
                if config.TEST_MODE_ACTIVE:
                    ban_msg = formatter.format_test_mode_message(ban_msg)
                
                if not config.SILENT_MODE_ACTIVE:
                    await context.bot.send_message(
                        chat_id=config.GROUP_ID,
                        message_thread_id=config.TOPIC_ADMINISTRACION,
                        text=ban_msg
                    )
                
                await ModerationModule._send_alert(user_id, message.from_user.username, user_data, 'flood_reiterado', 'Múltiples mensajes', 'BAN', context)
            else:
                # Solo warning
                warning_msg = formatter.format_warning_message('flood', 'media')
                if config.TEST_MODE_ACTIVE:
                    warning_msg = formatter.format_test_mode_message(warning_msg)
                
                if not config.SILENT_MODE_ACTIVE:
                    await context.bot.send_message(
                        chat_id=config.GROUP_ID,
                        message_thread_id=config.TOPIC_ADMINISTRACION,
                        text=warning_msg
                    )
                
                await ModerationModule._send_alert(user_id, message.from_user.username, user_data, 'flood', 'Múltiples mensajes', 'warning', context)
            
            # Limpiar contador
            user_message_times[user_id] = []
            return True
        
        return False
    
    @staticmethod
    async def _check_repeated_message(user_id: int, text: str, message: Message, user_data: dict, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Verificar mensajes repetidos"""
        if not text:
            return False
        
        # Verificar si es el mismo mensaje que el anterior
        if user_last_messages[user_id] == text:
            user_repeat_count[user_id] += 1
        else:
            user_last_messages[user_id] = text
            user_repeat_count[user_id] = 1
        
        # Si repite 4 veces o más
        if user_repeat_count[user_id] >= config.REPEATED_MESSAGE_THRESHOLD:
            # Borrar mensaje repetido
            if not config.TEST_MODE_ACTIVE:
                await message.delete()
            
            # Agregar warning
            await db_manager.add_warning(
                user_id=user_id,
                warning_type='repeticion',
                severity='leve',
                message_text=text,
                message_id=message.message_id,
                chat_id=message.chat_id,
                topic_id=message.message_thread_id,
                action_taken='delete+warning'
            )
            
            await db_manager.add_risk_event(
                user_id=user_id,
                event_type='repeticion',
                risk_points=config.RISK_POINTS['repeticion'],
                description='Mensaje repetido múltiples veces'
            )
            
            warning_msg = formatter.format_warning_message('repeticion', 'leve')
            if config.TEST_MODE_ACTIVE:
                warning_msg = formatter.format_test_mode_message(warning_msg)
            
            if not config.SILENT_MODE_ACTIVE:
                await context.bot.send_message(
                    chat_id=config.GROUP_ID,
                    message_thread_id=config.TOPIC_ADMINISTRACION,
                    text=warning_msg
                )
            
            # Castigo progresivo
            from modules.warnings import warnings_module
            await warnings_module.apply_progressive_punishment(user_id, user_data, context)
            
            await ModerationModule._send_alert(user_id, message.from_user.username, user_data, 'repeticion', text, 'delete+warning', context)
            
            # Resetear contador
            user_repeat_count[user_id] = 0
            return True
        
        return False
    
    @staticmethod
    async def _check_suspicious_file(message: Message, user_data: dict, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Verificar archivos sospechosos"""
        document = message.document
        if not document or not document.file_name:
            return False
        
        file_name = document.file_name.lower()
        suspicious_extensions = ['.apk', '.zip', '.exe', '.bat', '.cmd', '.sh']
        
        if any(file_name.endswith(ext) for ext in suspicious_extensions):
            user_id = message.from_user.id
            
            # Borrar archivo
            if not config.TEST_MODE_ACTIVE:
                await message.delete()
            
            # Warning
            await db_manager.add_warning(
                user_id=user_id,
                warning_type='archivo_sospechoso',
                severity='media',
                message_text=f"Archivo: {file_name}",
                message_id=message.message_id,
                chat_id=message.chat_id,
                topic_id=message.message_thread_id,
                action_taken='delete+warning'
            )
            
            await db_manager.add_risk_event(
                user_id=user_id,
                event_type='archivo_sospechoso',
                risk_points=config.RISK_POINTS['archivo_sospechoso'],
                description=f'Envió archivo sospechoso: {file_name}'
            )
            
            warning_msg = formatter.format_warning_message('archivo_sospechoso', 'media')
            if config.TEST_MODE_ACTIVE:
                warning_msg = formatter.format_test_mode_message(warning_msg)
            
            if not config.SILENT_MODE_ACTIVE:
                await context.bot.send_message(
                    chat_id=config.GROUP_ID,
                    message_thread_id=config.TOPIC_ADMINISTRACION,
                    text=warning_msg
                )
            
            # Castigo progresivo
            from modules.warnings import warnings_module
            await warnings_module.apply_progressive_punishment(user_id, user_data, context)
            
            await ModerationModule._send_alert(user_id, message.from_user.username, user_data, 'archivo_sospechoso', file_name, 'delete+warning', context)
            return True
        
        return False
    
    @staticmethod
    async def _check_forward_spam(user_id: int, message: Message, user_data: dict, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Verificar reenvíos masivos (simplificado)"""
        # Por ahora solo marcar como sospechoso
        await db_manager.add_risk_event(
            user_id=user_id,
            event_type='reenvio_masivo',
            risk_points=config.RISK_POINTS['reenvio_masivo'],
            description='Reenvió mensaje'
        )
        
        # Actualizar estado si el riesgo es alto
        risk_score = await db_manager.get_risk_score(user_id)
        if risk_score >= config.RISK_SCORE_SUSPICIOUS_THRESHOLD:
            await db_manager.update_user_status(user_id, 'sospechoso')
        
        return False
    
    @staticmethod
    async def _alert_ambiguous_case(message: Message, user_data: dict, case_type: str, context: ContextTypes.DEFAULT_TYPE):
        """Alertar caso ambiguo para decisión admin"""
        alert = f"⚠️ CASO AMBIGUO - {case_type}\n\n"
        alert += f"Usuario: @{message.from_user.username}\n"
        alert += f"ID: {message.from_user.id}\n"
        alert += f"Estado: {user_data['status']}\n\n"
        alert += f"Mensaje:\n{message.text[:200]}\n\n"
        alert += "¿Qué acción tomar?"
        
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        try:
            # Guardar el caso para aprendizaje futuro (pendiente de decisión)
            import json
            context_data = json.dumps({
                'chat_id': message.chat_id,
                'message_id': message.message_id,
                'user_id': message.from_user.id
            })
            
            case_id = await db_manager.save_learning_case(
                message_text=message.text,
                case_type=case_type,
                user_id=message.from_user.id,
                admin_decision='pending',
                context_data=context_data
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Falso Positivo", callback_data=f"learn_ignore|{case_id}"),
                    InlineKeyboardButton("⚠️ Warning", callback_data=f"learn_warn|{case_id}")
                ],
                [
                    InlineKeyboardButton("🛑 Mute", callback_data=f"learn_mute|{case_id}"),
                    InlineKeyboardButton("🔨 Ban", callback_data=f"learn_ban|{case_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID,
                text=alert,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Error enviando alerta ambigua: {e}")
    
    @staticmethod
    async def _send_alert(user_id: int, username: str, user_data: dict, motivo: str, mensaje_texto: str, accion: str, context: ContextTypes.DEFAULT_TYPE):
        """Enviar alerta al tema de alertas en grupo de respaldo"""
        warnings_count = await db_manager.get_warning_count(user_id)
        risk_score = await db_manager.get_risk_score(user_id)
        
        alert = formatter.format_alert(
            user_id=user_id,
            username=username,
            user_status=user_data['status'],
            motivo=motivo,
            mensaje_texto=mensaje_texto,
            accion=accion,
            warnings_count=warnings_count,
            risk_score=risk_score
        )
        
        try:
            await context.bot.send_message(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID,
                text=alert
            )
        except Exception as e:
            print(f"Error enviando alerta: {e}")

# Instancia global
moderation_module = ModerationModule()
