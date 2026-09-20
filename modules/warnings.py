"""
Módulo de Warnings
Gestiona el sistema de advertencias y castigos progresivos
"""

from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import config
from database.db_manager import db_manager
from utils.formatters import formatter

class WarningsModule:
    
    async def apply_progressive_punishment(self, user_id: int, user_data: dict, context: ContextTypes.DEFAULT_TYPE):
        """
        Aplicar castigo progresivo según número de warnings
        2 warnings = mute 1h
        4 warnings = ban
        """
        warnings_count = await db_manager.get_warning_count(user_id)
        
        if warnings_count >= config.MAX_WARNINGS_BEFORE_BAN:
            # Ban automático
            if not config.TEST_MODE_ACTIVE:
                await context.bot.ban_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
                await db_manager.ban_user(user_id)
            
            await db_manager.log_moderation_action(
                user_id=user_id,
                action_type='ban',
                reason=f'{warnings_count} warnings acumuladas',
                auto_action=True
            )
            
            ban_msg = formatter.format_ban_message()
            if config.TEST_MODE_ACTIVE:
                ban_msg = formatter.format_test_mode_message(ban_msg)
            
            if not config.SILENT_MODE_ACTIVE:
                await context.bot.send_message(
                    chat_id=config.GROUP_ID,
                    message_thread_id=config.TOPIC_ADMINISTRACION,
                    text=ban_msg
                )
        
        elif warnings_count >= 2:
            # Mute progresivo
            if warnings_count == 2:
                duration = config.MUTE_DURATION_1  # 1 hora
            elif warnings_count == 3:
                duration = config.MUTE_DURATION_2  # 6 horas
            else:
                duration = config.MUTE_DURATION_3  # 24 horas
            
            if not config.TEST_MODE_ACTIVE:
                until_date = datetime.now() + timedelta(minutes=duration)
                await context.bot.restrict_chat_member(
                    chat_id=config.GROUP_ID,
                    user_id=user_id,
                    permissions={"can_send_messages": False},
                    until_date=until_date
                )
            
            await db_manager.log_moderation_action(
                user_id=user_id,
                action_type='mute',
                reason=f'{warnings_count} warnings',
                duration=duration,
                auto_action=True
            )
            
            mute_msg = formatter.format_mute_message(duration)
            if config.TEST_MODE_ACTIVE:
                mute_msg = formatter.format_test_mode_message(mute_msg)
            
            if not config.SILENT_MODE_ACTIVE:
                await context.bot.send_message(
                    chat_id=config.GROUP_ID,
                    message_thread_id=config.TOPIC_ADMINISTRACION,
                    text=mute_msg
                )
    
    async def check_trusted_warnings_loss(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """
        Verificar si un usuario trusted debe perder su estado por warnings
        Pierde trusted automáticamente con 3 warnings
        """
        user_data = await db_manager.get_user(user_id)
        if not user_data or user_data['status'] != 'trusted':
            return
        
        warnings_count = await db_manager.get_warning_count(user_id)
        
        if warnings_count >= config.TRUSTED_WARNINGS_TO_LOSE:
            # Perder estado trusted
            await db_manager.demote_from_trusted(user_id, f'{warnings_count} warnings')
            
            # Enviar mensaje de apelación
            appeal_msg = f"Has perdido tu estado de usuario trusted debido a {warnings_count} advertencias.\n\n"
            appeal_msg += "Si consideras que esto fue un error, puedes apelar enviando un mensaje privado a @admin."
            
            if not config.TEST_MODE_ACTIVE:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=appeal_msg
                    )
                except:
                    # Si no se puede enviar por privado, enviar en administración
                    await context.bot.send_message(
                        chat_id=config.GROUP_ID,
                        message_thread_id=config.TOPIC_ADMINISTRACION,
                        text=f"@{user_data['username']}: {appeal_msg}"
                    )

# Instancia global
warnings_module = WarningsModule()
