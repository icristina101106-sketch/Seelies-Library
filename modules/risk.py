"""
Módulo de Sistema de Riesgo
Calcula y gestiona el score de riesgo de usuarios
"""

from telegram.ext import ContextTypes
import config
from database.db_manager import db_manager

class RiskModule:
    
    async def update_user_status_by_risk(self, user_id: int):
        """Actualizar estado del usuario según su score de riesgo"""
        user_data = await db_manager.get_user(user_id)
        if not user_data:
            return
        
        risk_score = user_data['risk_score']
        current_status = user_data['status']
        
        # No cambiar estado de trusted o baneados
        if current_status in ['trusted', 'baneado']:
            return
        
        # Determinar nuevo estado según riesgo
        if risk_score >= config.RISK_SCORE_SUSPICIOUS_THRESHOLD:
            new_status = 'sospechoso'
        elif risk_score >= config.RISK_SCORE_OBSERVED_THRESHOLD:
            new_status = 'observado'
        else:
            new_status = 'normal'
        
        # Actualizar si cambió
        if new_status != current_status:
            await db_manager.update_user_status(user_id, new_status)
    
    async def check_risk_threshold(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Verificar si el usuario llegó al umbral de riesgo para ban
        Retorna True si debe ser baneado
        """
        risk_score = await db_manager.get_risk_score(user_id)
        
        if risk_score >= config.RISK_SCORE_BAN_THRESHOLD:
            # Umbral de ban alcanzado
            user_data = await db_manager.get_user(user_id)
            
            # Enviar alerta al admin para decisión
            alert = f"⚠️ UMBRAL DE RIESGO ALCANZADO\n\n"
            alert += f"Usuario: @{user_data['username']}\n"
            alert += f"ID: {user_id}\n"
            alert += f"Riesgo: {risk_score}/{config.RISK_SCORE_BAN_THRESHOLD}\n"
            alert += f"Estado: {user_data['status']}\n"
            alert += f"Warnings: {user_data['warnings_count']}\n\n"
            alert += "Se recomienda ban automático.\n"
            alert += "Usa /ban {user_id} para confirmar."
            
            await context.bot.send_message(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID,
                text=alert
            )
            
            # Ban automático si está configurado
            if config.MODE == "produccion" and not config.TEST_MODE_ACTIVE:
                await context.bot.ban_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
                await db_manager.ban_user(user_id)
                
                await db_manager.log_moderation_action(
                    user_id=user_id,
                    action_type='ban',
                    reason=f'Riesgo {risk_score} alcanzó umbral',
                    auto_action=True
                )
                
                return True
        
        return False
    
    async def alert_before_threshold(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Alertar cuando el usuario está cerca del umbral de ban"""
        risk_score = await db_manager.get_risk_score(user_id)
        
        # Alertar cuando está a 2-3 puntos del umbral
        if config.RISK_SCORE_BAN_THRESHOLD - risk_score <= 3:
            user_data = await db_manager.get_user(user_id)
            
            alert = f"⚠️ USUARIO CERCA DEL UMBRAL DE RIESGO\n\n"
            alert += f"Usuario: @{user_data['username']}\n"
            alert += f"ID: {user_id}\n"
            alert += f"Riesgo: {risk_score}/{config.RISK_SCORE_BAN_THRESHOLD}\n"
            alert += f"Estado: {user_data['status']}\n"
            alert += f"Warnings: {user_data['warnings_count']}\n\n"
            alert += "Vigilancia aumentada recomendada."
            
            await context.bot.send_message(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID,
                text=alert
            )
    
    async def check_dangerous_combinations(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """
        Detectar combinaciones peligrosas de eventos
        Ejemplo: usuario nuevo + sin foto + link + flood
        """
        user_data = await db_manager.get_user(user_id)
        if not user_data:
            return
        
        # Combinación peligrosa: nuevo + sin foto + alta actividad sospechosa
        if (user_data['status'] == 'nuevo' and 
            not user_data['has_photo'] and 
            user_data['warnings_count'] >= 2):
            
            # Agregar puntos extra de riesgo
            await db_manager.add_risk_event(
                user_id=user_id,
                event_type='combinacion_peligrosa',
                risk_points=config.RISK_POINTS['combinacion_peligrosa'],
                description='Combinación: nuevo + sin foto + múltiples warnings'
            )
            
            # Alerta
            alert = f"🚨 COMBINACIÓN PELIGROSA DETECTADA\n\n"
            alert += f"Usuario: @{user_data['username']}\n"
            alert += f"ID: {user_id}\n"
            alert += f"Patrón: Usuario nuevo + Sin foto + {user_data['warnings_count']} warnings\n"
            alert += f"Riesgo actual: {user_data['risk_score']}\n\n"
            alert += "Se recomienda revisión."
            
            # Mute preventivo temporal (30 mins)
            from datetime import datetime, timedelta
            from telegram import ChatPermissions
            try:
                await context.bot.restrict_chat_member(
                    chat_id=config.GROUP_ID,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now() + timedelta(minutes=30)
                )
                alert += "\n\n🔇 **Acción automática:** El usuario ha sido silenciado preventivamente por 30 minutos mientras lo revisan."
                await db_manager.log_moderation_action(user_id, 'mute', 'Mute preventivo 30m por combinación de riesgo')
            except Exception as e:
                alert += f"\n\n❌ Error al silenciar automáticamente: {e}"
            
            await context.bot.send_message(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID if hasattr(config, 'ALERT_TOPIC_ID') else None,
                text=alert
            )

# Instancia global
risk_module = RiskModule()
