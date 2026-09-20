"""
Módulo de Gestión de Usuarios
Maneja estados, foto de perfil, promoción a trusted
"""

from telegram import Update, User
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import json
import config
from database.db_manager import db_manager
from utils.text_analysis import text_analyzer
from utils.formatters import formatter

class UsersModule:

    def __init__(self):
        self.bot_info = None
        self.recent_joins = []
    
    async def handle_join_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Interceptar solicitud de unión, enviar reglas por DM y programar rechazo a 24h."""
        from modules import toggles
        if not toggles.is_enabled("entradas"):
            return
            
        join_request = update.chat_join_request
        user = join_request.from_user
        chat_id = join_request.chat.id
        
        # Detector de picos de requests (Fase 4)
        import time
        now = time.time()
        self.recent_joins = [t for t in self.recent_joins if now - t < 300] # Limpiar > 5 mins
        self.recent_joins.append(now)
        
        if getattr(config, 'PAUSE_JOIN_REQUESTS', False) or len(self.recent_joins) > 10:
            if not getattr(config, 'PAUSE_JOIN_REQUESTS', False):
                config.PAUSE_JOIN_REQUESTS = True
                try:
                    await context.bot.send_message(
                        chat_id=config.ALERT_GROUP_ID,
                        message_thread_id=config.ALERT_TOPIC_ID if hasattr(config, 'ALERT_TOPIC_ID') else None,
                        text="⚠️ **ALERTA CRÍTICA: POSIBLE RAID DETECTADO** ⚠️\n\nSe han recibido más de 10 solicitudes de entrada en menos de 5 minutos. **EL MODO BAJO PERFIL HA SIDO ACTIVADO AUTOMÁTICAMENTE.**\n\nTodas las nuevas solicitudes serán declinadas hasta que se normalice la situación.",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass
            # Declinar automáticamente en modo bajo perfil
            try:
                await join_request.decline()
                await context.bot.send_message(
                    chat_id=user.id,
                    text="❌ Lo sentimos, debido a un volumen inusual de solicitudes, el grupo no está aceptando nuevos miembros en este momento. Intenta nuevamente más tarde."
                )
            except:
                pass
            return

        # Filtro de Foto
        photos = await context.bot.get_user_profile_photos(user.id)
        if photos.total_count == 0:
            try:
                await join_request.decline()
                await context.bot.send_message(
                    chat_id=user.id,
                    text="❌ **Solicitud Rechazada:**\nPara unirte a nuestra comunidad es obligatorio tener una foto de perfil pública (no la inicial de color por defecto). Por favor, colócate una foto en tus ajustes de privacidad e intenta de nuevo."
                )
            except:
                pass
            return
            
        # Filtro de Nombre Limpio
        import re
        full_name = f"{user.first_name} {user.last_name or ''}".strip()
        # Rechazar caracteres árabes (\u0600-\u06FF), cirílicos (\u0400-\u04FF), 
        # y fuentes matemáticas raras (\U0001D400-\U0001D7FF)
        if re.search(r'[\u0600-\u06FF\u0400-\u04FF]', full_name) or re.search(r'[\U0001D400-\U0001D7FF]', full_name):
            try:
                await join_request.decline()
                await context.bot.send_message(
                    chat_id=user.id,
                    text="❌ **Solicitud Rechazada:**\nTu nombre contiene caracteres no permitidos, símbolos extraños o fuentes anómalas. Por favor, usa letras estándar e intenta nuevamente."
                )
            except:
                pass
            return

        # Si pasa los filtros, auto-aprobar
        try:
            await join_request.approve()
            
            # Enviar mensaje de bienvenida directo
            from utils.formatters import get_welcome_image_path
            from modules.faq import send_faq_dm
            import os
            
            photo_path = get_welcome_image_path()
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, 'rb') as f:
                    await context.bot.send_photo(chat_id=user.id, photo=f)
                    
            await send_faq_dm(context.bot, user.id, user.first_name)
            
            # Guardar el request en DB para que no se pierda el registro de entrada
            await db_manager.save_join_request(user.id, chat_id)
            await db_manager.approve_join_request(user.id, chat_id)
            
        except Exception as e:
            print(f"Error en auto-aceptar: {e}")
            try:
                await context.bot.decline_chat_join_request(
                    chat_id=chat_id,
                    user_id=user.id
                )
                await db_manager.save_join_request(user.id, chat_id)
                await db_manager.update_join_request_status(user.id, chat_id, 'declined_no_dm')
            except Exception:
                pass
            try:
                await context.bot.send_message(
                    chat_id=config.ALERT_GROUP_ID,
                    message_thread_id=config.ALERT_TOPIC_ID,
                    text=(
                        f"🚫 Solicitud rechazada: no se pudo enviar DM\n"
                        f"Usuario: @{user.username or user.first_name} ({user.id})"
                    )
                )
            except Exception:
                pass
                
    async def handle_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar nuevo miembro que entra al grupo"""
        for new_member in update.message.new_chat_members:
            user_id = new_member.id
            username = new_member.username
            first_name = new_member.first_name
            last_name = new_member.last_name
            
            # Verificar si tiene foto
            has_photo = False
            try:
                photos = await context.bot.get_user_profile_photos(user_id, limit=1)
                has_photo = photos.total_count > 0
            except:
                pass
            
            # Crear usuario en BD
            await db_manager.create_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                has_photo=has_photo
            )
            
            # Verificar si es sospechoso
            await self.check_suspicious_user(user_id, new_member, context)
            
            # Si no tiene foto, programar deadline
            if not has_photo:
                await self.schedule_photo_deadline(user_id, username, context)
            
            # Enviar bienvenida
            await self.send_welcome(user_id, username, first_name, context)
    
    async def check_suspicious_user(self, user_id: int, user: User, context: ContextTypes.DEFAULT_TYPE):
        """Verificar si un usuario es sospechoso"""
        is_suspicious = False
        reasons = []
        
        # Sin foto
        try:
            photos = await context.bot.get_user_profile_photos(user_id, limit=1)
            if photos.total_count == 0:
                is_suspicious = True
                reasons.append('sin_foto')
                await db_manager.add_risk_event(
                    user_id=user_id,
                    event_type='sin_foto',
                    risk_points=config.RISK_POINTS['sin_foto'],
                    description='Usuario sin foto de perfil'
                )
        except:
            pass
        
        # Sin username
        if not user.username:
            is_suspicious = True
            reasons.append('sin_username')
            await db_manager.add_risk_event(
                user_id=user_id,
                event_type='sin_username',
                risk_points=config.RISK_POINTS['sin_username'],
                description='Usuario sin username'
            )
        
        # Posible cuenta evasora (mismo nombre que baneado)
        banned_names = await db_manager.get_banned_user_names()
        if user.first_name and user.first_name.lower() in banned_names:
            is_suspicious = True
            reasons.append('posible_evasor')
            await db_manager.add_risk_event(
                user_id=user_id,
                event_type='evasor',
                risk_points=10,  # Alta puntuación
                description=f'Nombre coincide con baneado: {user.first_name}'
            )

        # Nombre raro
        if text_analyzer.is_suspicious_name(user.first_name):
            is_suspicious = True
            reasons.append('nombre_raro')
            await db_manager.add_risk_event(
                user_id=user_id,
                event_type='nombre_raro',
                risk_points=config.RISK_POINTS['nombre_raro'],
                description=f'Nombre sospechoso: {user.first_name}'
            )
        
        # Si es sospechoso, marcar y enviar alerta
        if is_suspicious:
            await db_manager.update_user_status(user_id, 'sospechoso')
            
            # NUEVO: Enviar alerta al grupo de alertas
            reasons_text = ', '.join(reasons)
            risk_score = await db_manager.get_risk_score(user_id)
            
            alert = f"🚨 USUARIO NUEVO SOSPECHOSO\n"
            alert += "=" * 40 + "\n\n"
            alert += f"👤 Usuario: @{user.username or user.first_name}\n"
            alert += f"   ID: {user_id}\n\n"
            alert += f"⚠️ Razones: {reasons_text}\n"
            alert += f"🎯 Riesgo actual: {risk_score}\n\n"
            alert += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            try:
                await context.bot.send_message(
                    chat_id=config.ALERT_GROUP_ID,
                    message_thread_id=config.ALERT_TOPIC_ID,
                    text=alert
                )
            except Exception as e:
                print(f"Error enviando alerta sospechoso: {e}")
    
    async def schedule_photo_deadline(self, user_id: int, username: str, context: ContextTypes.DEFAULT_TYPE):
        """Programar deadline de 24h para foto de perfil"""
        multiplier = 1
        vacation = await db_manager.get_setting('vacation_mode', 'false')
        if vacation == 'true':
            multiplier = getattr(config, 'VACATION_TOLERANCE_MULTIPLIER', 2)
            
        deadline = datetime.now() + timedelta(hours=config.PHOTO_DEADLINE_HOURS * multiplier)
        
        # Actualizar en BD
        await db_manager.update_user_photo_status(user_id, False, deadline)
        
        # Programar tarea de expulsión
        await db_manager.schedule_task(
            task_type='kick_no_photo',
            target_id=user_id,
            execute_at=deadline
        )
        
        # Programar recordatorio a las 12h
        reminder_time = datetime.now() + timedelta(hours=config.PHOTO_REMINDER_HOURS)
        await db_manager.schedule_task(
            task_type='photo_reminder',
            target_id=user_id,
            execute_at=reminder_time
        )
        
        # Enviar aviso en administración
        warning_msg = formatter.format_photo_warning(username, config.PHOTO_DEADLINE_HOURS)
        
        await context.bot.send_message(
            chat_id=config.GROUP_ID,
            message_thread_id=config.TOPIC_ADMINISTRACION,
            text=warning_msg
        )
        
        # Intentar enviar por privado también
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=warning_msg
            )
        except:
            pass
    
    async def send_photo_reminder(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Enviar recordatorio de foto a las 12h"""
        user_data = await db_manager.get_user(user_id)
        if not user_data or user_data['has_photo']:
            return
        
        # Verificar si ya se envió el recordatorio
        if user_data['photo_reminder_sent']:
            return
        
        # Marcar como enviado
        await db_manager.set_photo_reminder_sent(user_id)
        
        # Enviar recordatorio
        reminder_msg = formatter.format_photo_reminder(user_data['username'])
        
        await context.bot.send_message(
            chat_id=config.GROUP_ID,
            message_thread_id=config.TOPIC_ADMINISTRACION,
            text=reminder_msg
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=reminder_msg
            )
        except:
            pass
    
    async def kick_user_no_photo(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Expulsar usuario que no puso foto en 24h"""
        user_data = await db_manager.get_user(user_id)
        if not user_data:
            return
        
        # Verificar si ahora tiene foto
        try:
            photos = await context.bot.get_user_profile_photos(user_id, limit=1)
            if photos.total_count > 0:
                # Tiene foto ahora, cancelar expulsión
                await db_manager.update_user_photo_status(user_id, True, None)
                return
        except:
            pass
        
        # Expulsar
        if not config.TEST_MODE_ACTIVE:
            try:
                await context.bot.ban_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
                # Desbanear inmediatamente para que pueda volver a entrar
                await context.bot.unban_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
            except:
                pass
        
        # Registrar acción
        await db_manager.log_moderation_action(
            user_id=user_id,
            action_type='kick',
            reason='Sin foto de perfil después de 24h',
            auto_action=True
        )
        
        # Notificar
        kick_msg = f"@{user_data['username']} fue removido por no actualizar su foto de perfil."
        if config.TEST_MODE_ACTIVE:
            kick_msg = formatter.format_test_mode_message(kick_msg)
        
        await context.bot.send_message(
            chat_id=config.GROUP_ID,
            message_thread_id=config.TOPIC_ADMINISTRACION,
            text=kick_msg
        )
    
    async def send_welcome(self, user_id: int, username: str, first_name: str, context: ContextTypes.DEFAULT_TYPE):
        """Enviar mensaje de bienvenida con imagen opcional y auto-borrado en 5 min"""
        # Generar mensaje de bienvenida
        welcome_msg = formatter.format_welcome_message(username, first_name)
        
        # Verificar si hay imagen de bienvenida
        image_path = formatter.get_welcome_image_path()
        sent_message = None
        
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Probar el Buscador", callback_data="tour_buscar")],
            [InlineKeyboardButton("📚 Ver Directorio", callback_data="dir_home")]
        ])
        
        if image_path:
            # Enviar con imagen
            try:
                with open(image_path, 'rb') as photo:
                    kwargs = {
                        'chat_id': config.GROUP_ID,
                        'photo': photo,
                        'caption': welcome_msg,
                        'reply_markup': keyboard
                    }
                    if config.TOPIC_GENERAL:
                        kwargs['message_thread_id'] = config.TOPIC_GENERAL
                    sent_message = await context.bot.send_photo(**kwargs)
            except Exception as e:
                print(f"Error enviando imagen de bienvenida: {e}")
                kwargs = {
                    'chat_id': config.GROUP_ID,
                    'text': welcome_msg,
                    'reply_markup': keyboard
                }
                if config.TOPIC_GENERAL:
                    kwargs['message_thread_id'] = config.TOPIC_GENERAL
                sent_message = await context.bot.send_message(**kwargs)
        else:
            kwargs = {
                'chat_id': config.GROUP_ID,
                'text': welcome_msg,
                'reply_markup': keyboard
            }
            if config.TOPIC_GENERAL:
                kwargs['message_thread_id'] = config.TOPIC_GENERAL
            sent_message = await context.bot.send_message(**kwargs)
        
        # Programar borrado automático del mensaje de bienvenida en 5 minutos
        if sent_message:
            import asyncio
            async def delete_welcome():
                await asyncio.sleep(300)  # 5 minutos
                try:
                    await context.bot.delete_message(
                        chat_id=sent_message.chat_id,
                        message_id=sent_message.message_id
                    )
                except Exception:
                    pass
            asyncio.create_task(delete_welcome())
        
        # Enviar FAQ por DM al nuevo miembro
        from modules.faq import send_faq_dm
        await send_faq_dm(user_id, context)
    
    async def check_trusted_promotion(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Verificar si un usuario debe ser promovido a trusted automáticamente"""
        user_data = await db_manager.get_user(user_id)
        if not user_data or user_data['status'] == 'trusted':
            return
        
        # Verificar requisitos
        join_date = datetime.fromisoformat(user_data['join_date'])
        days_in_group = (datetime.now() - join_date).days
        
        requirements = config.TRUSTED_REQUIREMENTS
        
        if (days_in_group >= requirements['days_in_group'] and
            user_data['warnings_count'] <= requirements['max_warnings'] and
            user_data['risk_score'] <= requirements['max_risk'] and
            user_data['has_photo'] == requirements['has_photo'] and
            not user_data['is_banned']):
            
            # Promover a trusted
            await db_manager.promote_to_trusted(user_id)
            
            # Notificar
            congrats_msg = f"🌟 @{user_data['username']} ha sido promovido a usuario trusted.\n"
            congrats_msg += "Sus warnings se reiniciarán cada 2 semanas y su riesgo disminuirá con el tiempo."
            
            await context.bot.send_message(
                chat_id=config.GROUP_ID,
                message_thread_id=config.TOPIC_ADMINISTRACION,
                text=congrats_msg
            )
            
            # Alerta al admin
            alert = f"✅ PROMOCIÓN AUTOMÁTICA A TRUSTED\n\n"
            alert += f"Usuario: @{user_data['username']}\n"
            alert += f"ID: {user_id}\n"
            alert += f"Días en grupo: {days_in_group}\n"
            alert += f"Warnings: {user_data['warnings_count']}\n"
            alert += f"Riesgo: {user_data['risk_score']}"
            
            await context.bot.send_message(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID,
                text=alert
            )

# Instancia global
users_module = UsersModule()
