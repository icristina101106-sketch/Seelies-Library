"""
Módulo Scheduler
Tareas programadas y automáticas
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import ContextTypes
from datetime import datetime
import asyncio
import os
import config
from database.db_manager import db_manager

class SchedulerModule:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def start(self, context: ContextTypes.DEFAULT_TYPE):
        """Iniciar scheduler con todas las tareas"""
        # Verificar tareas pendientes cada minuto
        self.scheduler.add_job(
            self.check_pending_tasks,
            'interval',
            minutes=1,
            args=[context]
        )
        
        # Reducir riesgo de usuarios trusted cada 24 horas
        self.scheduler.add_job(
            self.reduce_trusted_risk,
            'interval',
            hours=24,
            args=[context]
        )
        
        # Resetear warnings de trusted cada 2 semanas (domingo a las 00:00)
        self.scheduler.add_job(
            self.reset_trusted_warnings,
            'cron',
            day_of_week='sun',
            hour=0,
            minute=0,
            args=[context]
        )
        
        # Verificar promociones a trusted cada día
        self.scheduler.add_job(
            self.check_trusted_promotions,
            'interval',
            hours=24,
            args=[context]
        )
        
        # Reporte semanal (Domingo 23:00)
        self.scheduler.add_job(
            self.generate_weekly_report,
            'cron',
            day_of_week=config.WEEKLY_REPORT_DAY,
            hour=config.WEEKLY_REPORT_HOUR,
            minute=0,
            args=[context]
        )

        # Mantenimiento semanal: backup de BD + enlaces rotos (Domingo 03:00)
        self.scheduler.add_job(
            self.weekly_maintenance,
            'cron',
            day_of_week=config.WEEKLY_MAINTENANCE_DAY,
            hour=config.WEEKLY_MAINTENANCE_HOUR,
            minute=0,
            args=[context]
        )
        
        # Resurgimiento de pedidos (Día 1 del mes a las 10:00 AM)
        self.scheduler.add_job(
            self.resurrect_requests,
            'cron',
            day=1,
            hour=10,
            minute=0,
            args=[context]
        )
        
        # Newsletter los viernes a las 18:00
        self.scheduler.add_job(
            self.friday_newsletter,
            'cron',
            day_of_week='fri',
            hour=18,
            minute=0,
            args=[context]
        )
        
        # Reporte de admins los lunes a las 09:00
        self.scheduler.add_job(
            self.monday_admin_report,
            'cron',
            day_of_week='mon',
            hour=9,
            minute=0,
            args=[context]
        )
        
        # Aportador de la semana los domingos a las 12:00
        self.scheduler.add_job(
            self.sunday_top_uploader,
            'cron',
            day_of_week='sun',
            hour=12,
            minute=0,
            args=[context]
        )
        
        # Indulto mensual el día 1 de cada mes
        self.scheduler.add_job(
            self.monthly_pardon,
            'cron',
            day=1,
            hour=12,
            minute=0,
            args=[context]
        )
        
        # Revisión de pedidos antiguos (Diario a las 12:00)
        self.scheduler.add_job(
            self.check_old_requests,
            'cron',
            hour=12,
            minute=0,
            args=[context]
        )
        
        # Purga mensual el día 15 de cada mes
        self.scheduler.add_job(
            self.monthly_purge_inactives,
            'cron',
            day=15,
            hour=12,
            minute=0,
            args=[context]
        )
        
        # Frase literaria (Diario a las 09:00 AM)
        self.scheduler.add_job(
            self.daily_quote,
            'cron',
            hour=9,
            minute=0,
            args=[context]
        )
        
        self.scheduler.start()
        print("OK - Scheduler iniciado")
    
    async def check_pending_tasks(self, context: ContextTypes.DEFAULT_TYPE):
        """Verificar y ejecutar tareas pendientes"""
        tasks = await db_manager.get_pending_tasks()
        
        for task in tasks:
            task_type = task['task_type']
            target_id = task['target_id']
            
            try:
                if task_type == 'kick_no_photo':
                    from modules.users import users_module
                    await users_module.kick_user_no_photo(target_id, context)
                
                elif task_type == 'photo_reminder':
                    from modules.users import users_module
                    await users_module.send_photo_reminder(target_id, context)
                
                elif task_type == 'delete_request':
                    # Eliminar pedido automáticamente
                    await self.delete_request(target_id, context)
                
                elif task_type == 'delete_message':
                    # Eliminar mensaje específico (ej: pedido incorrecto)
                    import json
                    extra_data = json.loads(task.get('extra_data', '{}') or '{}')
                    chat_id = extra_data.get('chat_id', config.GROUP_ID)
                    thread_id = extra_data.get('thread_id')
                    
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id,
                            message_id=target_id
                        )
                        print(f"OK - Mensaje {target_id} borrado (pedido incorrecto)")
                    except Exception as e:
                        print(f"Error borrando mensaje {target_id}: {e}")

                elif task_type == 'decline_join_request':
                    import json
                    extra_data = json.loads(task.get('extra_data') or '{}')
                    chat_id = extra_data.get('chat_id', config.GROUP_ID)
                    pending = await db_manager.get_join_request(target_id, chat_id)
                    if pending and pending.get('status') != 'pending':
                        await db_manager.complete_task(task['id'])
                        continue
                    try:
                        await context.bot.decline_chat_join_request(
                            chat_id=chat_id,
                            user_id=target_id
                        )
                        await db_manager.update_join_request_status(
                            target_id, chat_id, 'declined_timeout'
                        )
                        print(f"OK - Join request rechazada por timeout: {target_id}")
                    except Exception as e:
                        print(f"Error rechazando join request {target_id}: {e}")
                
                # Marcar tarea como completada
                await db_manager.complete_task(task['id'])
                
            except Exception as e:
                print(f"Error ejecutando tarea {task['id']}: {e}")
    
    async def delete_request(self, request_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Eliminar mensaje de pedido atendido del grupo"""
        import aiosqlite
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT message_id FROM book_requests WHERE id = ?", (request_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    message_id = row['message_id']
                    try:
                        await context.bot.delete_message(
                            chat_id=config.GROUP_ID,
                            message_id=message_id
                        )
                    except Exception as e:
                        print(f"Error borrando pedido {request_id}: {e}")
                    
                    # Marcar como eliminado
                    await db.execute(
                        "UPDATE book_requests SET deleted = 1 WHERE id = ?",
                        (request_id,)
                    )
                    await db.commit()
    
    async def reduce_trusted_risk(self, context: ContextTypes.DEFAULT_TYPE):
        """Reducir riesgo de usuarios trusted con el tiempo"""
        await db_manager.reduce_risk_over_time()
        print("OK - Riesgo de usuarios trusted reducido")
    
    async def reset_trusted_warnings(self, context: ContextTypes.DEFAULT_TYPE):
        """Resetear warnings de usuarios trusted cada 2 semanas"""
        await db_manager.reset_trusted_warnings()
        
        # Notificar al admin
        await context.bot.send_message(
            chat_id=config.ALERT_GROUP_ID,
            message_thread_id=config.ALERT_TOPIC_ID,
            text="OK - Warnings de usuarios trusted reseteadas (cada 2 semanas)"
        )
        print("OK - Warnings de trusted reseteadas")
    
    async def check_trusted_promotions(self, context: ContextTypes.DEFAULT_TYPE):
        """Verificar usuarios elegibles para promoción a trusted"""
        import aiosqlite
        from modules.users import users_module
        
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id FROM users 
                WHERE status IN ('normal', 'observado') 
                AND is_banned = 0
                AND join_date <= datetime('now', '-60 days')
            """) as cursor:
                users = await cursor.fetchall()
        
        promoted = 0
        for user in users:
            try:
                await users_module.check_trusted_promotion(user['user_id'], context)
                promoted += 1
            except Exception as e:
                print(f"Error verificando promoción {user['user_id']}: {e}")
        
        print(f"OK - Verificación de promociones: {len(users)} evaluados")
        
    async def generate_weekly_report(self, context: ContextTypes.DEFAULT_TYPE):
        """Generar y enviar reporte semanal en formato .txt"""
        try:
            data = await db_manager.get_weekly_report_data()
            
            # Generar contenido del reporte
            report_lines = []
            report_lines.append(f"REPORTE SEMANAL - SEELIE BOT")
            report_lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            report_lines.append("=" * 40)
            report_lines.append("")
            
            report_lines.append("1. RESUMEN DE USUARIOS")
            report_lines.append("-" * 25)
            report_lines.append(f"• Nuevos miembros esta semana: {data['new_members']}")
            report_lines.append(f"• Nuevos usuarios trusted: {data['new_trusted']}")
            report_lines.append(f"• Miembros sospechosos actuales: {data['suspicious_users']}")
            report_lines.append(f"• Miembros sin foto actual: {data['no_photo_users']}")
            report_lines.append("")
            
            report_lines.append("2. MODERACIÓN Y SANCIONES")
            report_lines.append("-" * 25)
            report_lines.append(f"• Warnings emitidas: {data['warnings_issued']}")
            if data['warnings_by_type']:
                report_lines.append("  Desglose por tipo:")
                for w in data['warnings_by_type']:
                    report_lines.append(f"    - {w['type']}: {w['count']}")
            report_lines.append(f"• Mutes aplicados: {data['mutes']}")
            report_lines.append(f"• Bans realizados: {data['bans']}")
            report_lines.append(f"• Apelaciones recibidas: {data['appeals']}")
            report_lines.append("")
            
            report_lines.append("3. BIBLIOTECA Y PEDIDOS")
            report_lines.append("-" * 25)
            report_lines.append(f"• Pedidos incorrectos/rechazados: {data['incorrect_requests']}")
            report_lines.append(f"• Duplicados detectados: {data['duplicates']}")
            report_lines.append("")
            
            # Crear archivo temporal
            import os
            from tempfile import NamedTemporaryFile
            
            os.makedirs(config.EXPORTS_DIR, exist_ok=True)
            filename = f"reporte_semanal_{datetime.now().strftime('%Y%m%d')}.txt"
            filepath = os.path.join(config.EXPORTS_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
                
            # Enviar archivo al grupo de alertas
            with open(filepath, 'rb') as doc:
                await context.bot.send_document(
                    chat_id=config.ALERT_GROUP_ID,
                    message_thread_id=config.ALERT_TOPIC_ID,
                    document=doc,
                    caption=f"📊 Reporte Semanal - {datetime.now().strftime('%Y-%m-%d')}"
                )
                
            print("OK - Reporte semanal generado y enviado")
            
        except Exception as e:
            print(f"Error generando reporte semanal: {e}")

    def _bot(self, context):
        return context.bot if hasattr(context, 'bot') else context

    async def weekly_maintenance(self, context):
        """Backup de BD + escaneo de enlaces rotos."""
        await self.backup_database(context)
        await self.scan_broken_library_links(context)

    async def check_old_requests(self, context):
        """Verificar pedidos pendientes que tienen más de 15 días y notificar a los admins"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        old_requests = await db_manager.get_old_pending_requests(15)
        if not old_requests:
            return
            
        for req in old_requests:
            msg = f"⏳ **Recordatorio de pedido antiguo**\n\n"
            msg += f"El pedido **{req['title']}** (por {req['author']}) lleva más de 15 días sin respuesta.\n\n"
            msg += f"ID: `{req['id']}`\n"
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("❌ No encontrado", callback_data=f"oldreq_notfound|{req['id']}"),
                    InlineKeyboardButton("👁️ Ignorar", callback_data=f"oldreq_ignore|{req['id']}")
                ]
            ])
            
            await context.bot.send_message(
                chat_id=config.ADMIN_GROUP_ID,
                text=msg,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
    async def resurrect_requests(self, context):
        """Día 1 del mes: Resurgimiento de los pedidos más buscados."""
        import aiosqlite
        bot = self._bot(context)
        
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Buscar pedidos con más de 30 días, status 'pending', no borrados
            async with db.execute("""
                SELECT titulo, autor, idioma 
                FROM book_requests 
                WHERE status = 'pending' AND deleted = 0 
                AND timestamp <= datetime('now', '-30 days')
                ORDER BY timestamp ASC
                LIMIT 10
            """) as cursor:
                old_requests = await cursor.fetchall()
                
        if not old_requests:
            return
            
        msg = "📌 **Resumen Mensual: Los Más Buscados** 📌\n\n"
        msg += "Estos libros llevan más de 30 días en nuestra lista de deseos y aún nadie los ha encontrado. "
        msg += "¡Doble agradecimiento a quien logre subirlos a la biblioteca!\n\n"
        
        for i, req in enumerate(old_requests, 1):
            idioma = "🇪🇸" if "español" in req['idioma'].lower() else "🇬🇧"
            msg += f"{i}. {idioma} **{req['titulo']}** de _{req['autor']}_\n"
            
        try:
            await bot.send_message(
                chat_id=config.GROUP_ID,
                message_thread_id=config.TOPIC_PETICIONES,
                text=msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error enviando resurrect_requests: {e}")

    async def monday_admin_report(self, context):
        """Lunes: Resumen semanal para admins de tareas pendientes."""
        import aiosqlite
        bot = self._bot(context)
        
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Apelaciones pendientes
            async with db.execute("SELECT COUNT(*) FROM appeals WHERE status = 'pendiente'") as c:
                appeals = (await c.fetchone())[0]
                
            # Pedidos > 7 días sin atender
            async with db.execute("SELECT COUNT(*) FROM book_requests WHERE status = 'pendiente' AND deleted = FALSE AND published_date <= date('now', '-7 days')") as c:
                old_reqs = (await c.fetchone())[0]
                
            # Usuarios en observación
            async with db.execute("SELECT COUNT(*) FROM users WHERE risk_status = 'observado'") as c:
                observed = (await c.fetchone())[0]
                
            # Análisis de horarios de infractores
            async with db.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count 
                FROM warnings 
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY hour 
                ORDER BY count DESC 
                LIMIT 1
            """) as c:
                peak_hour_row = await c.fetchone()
                peak_hour = f"{peak_hour_row['hour']}:00 a {int(peak_hour_row['hour'])+1}:00 UTC" if peak_hour_row else "N/A"
                
        if appeals == 0 and old_reqs == 0 and observed == 0:
            return
            
        msg = "📊 **REPORTE DE TAREAS ADMINISTRATIVAS (Lunes)**\n\n"
        msg += f"⚖️ Apelaciones pendientes: {appeals}\n"
        msg += f"⏳ Pedidos > 7 días sin resolver: {old_reqs}\n"
        msg += f"👁️ Usuarios en observación: {observed}\n\n"
        msg += f"⏰ **Alerta de Horarios:** La mayor concentración de infracciones (spam/riesgo) ocurre de **{peak_hour}**. Se sugiere mayor vigilancia.\n\n"
        msg += "Usa `/apelaciones` y `/pendientes` para gestionar."
        
        try:
            await bot.send_message(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID if hasattr(config, 'ALERT_TOPIC_ID') else None,
                text=msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error enviando reporte de admins: {e}")

    async def friday_newsletter(self, context):
        """Viernes: Boletín informativo con resumen de la semana."""
        if self.is_silent_hours():
            return
            
        import aiosqlite
        from datetime import datetime, timedelta
        bot = self._bot(context)
        
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Contar libros añadidos en los últimos 7 días
            async with db.execute("""
                SELECT COUNT(*) as total 
                FROM library_backup 
                WHERE timestamp >= datetime('now', '-7 days') AND file_name IS NOT NULL
            """) as cursor:
                row = await cursor.fetchone()
                total_week = row['total'] if row else 0
                
            # Autor más popular de la semana
            async with db.execute("""
                SELECT file_name 
                FROM library_backup 
                WHERE timestamp >= datetime('now', '-7 days') AND file_name IS NOT NULL
            """) as cursor:
                rows = await cursor.fetchall()
                
        if total_week == 0:
            return
            
        import re
        from collections import Counter
        authors = []
        for r in rows:
            fname = r['file_name']
            clean = re.sub(r'\.\w+$', '', fname)
            parts = clean.split(' - ')
            if len(parts) >= 2:
                authors.append(parts[-1].strip())
                
        top_author_msg = ""
        if authors:
            top_author = Counter(authors).most_common(1)[0]
            if top_author[1] > 1:
                top_author_msg = f"El autor más popular esta semana fue **{top_author[0]}** con {top_author[1]} aportes.\n\n"
                
        msg = (
            "🎉 **¡Resumen Semanal de Selene!** 🎉\n\n"
            f"¡Esta semana nuestra biblioteca creció muchísimo! Hemos añadido **{total_week}** libros nuevos.\n\n"
            f"{top_author_msg}"
            "Recuerda que puedes usar:\n"
            "• `/lanzamientos` para ver lo más reciente.\n"
            "• `/buscar` para encontrar tu próxima lectura.\n"
            "• `/topaportadores` para ver a los héroes de la comunidad.\n\n"
            "¡Feliz fin de semana y feliz lectura! 📖✨"
        )
        
        try:
            await bot.send_message(
                chat_id=config.GROUP_ID,
                message_thread_id=config.TOPIC_GENERAL if hasattr(config, 'TOPIC_GENERAL') else None,
                text=msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error enviando newsletter: {e}")

    async def sunday_top_uploader(self, context):
        """Domingo: Anunciar al aportador de la semana."""
        import aiosqlite
        bot = self._bot(context)
        
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id, COUNT(*) as total 
                FROM library_backup 
                WHERE timestamp >= datetime('now', '-7 days') AND file_name IS NOT NULL AND user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                
            if not row:
                return
                
            top_user_id = row['user_id']
            total_books = row['total']
            
            if total_books < 3: # Solo anunciar si subió al menos 3
                return
                
            # Obtener nombre
            async with db.execute("SELECT username, first_name FROM users WHERE user_id = ?", (top_user_id,)) as cursor:
                user_row = await cursor.fetchone()
                if not user_row:
                    return
                
                uname = user_row['username'] or user_row['first_name']
                
        msg = "🌟 **¡APORTADOR DE LA SEMANA!** 🌟\n\n"
        msg += f"Queremos darle un reconocimiento especial a @{uname} por ser la persona que más libros compartió con la comunidad esta semana, ¡con un total de **{total_books}** aportes!\n\n"
        msg += "¡Muchas gracias por mantener viva nuestra biblioteca! 💖📚"
        
        try:
            await bot.send_message(
                chat_id=config.GROUP_ID,
                message_thread_id=config.TOPIC_GENERAL if hasattr(config, 'TOPIC_GENERAL') else None,
                text=msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error enviando top uploader: {e}")

    async def monthly_pardon(self, context):
        """1 de cada mes: Limpiar warnings de usuarios con 6 meses de buena conducta"""
        import aiosqlite
        bot = self._bot(context)
        
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id, warnings_count, first_name 
                FROM users 
                WHERE warnings_count > 0 
                AND last_warning_date <= date('now', '-180 days')
                AND status != 'baneado'
            """) as cursor:
                rows = await cursor.fetchall()
                
            for row in rows:
                user_id = row['user_id']
                await db.execute("UPDATE users SET warnings_count = 0, risk_score = risk_score / 2 WHERE user_id = ?", (user_id,))
                await db.commit()
                
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text="🕊️ **¡Noticias de Selene!**\n\nHan pasado más de 6 meses desde tu última advertencia. Como recompensa por tu buena conducta, he limpiado tu historial de advertencias a cero.\n\n¡Gracias por mantener un ambiente agradable! 💖",
                        parse_mode='Markdown'
                    )
                except: pass

    async def backup_database(self, context):
        """Exportar bot_database y enviarla al grupo de alertas."""
        bot = self._bot(context)
        
    async def monthly_purge_inactives(self, context):
        """15 de cada mes: Generar TXT con usuarios inactivos > 3 meses."""
        import aiosqlite
        import io
        bot = self._bot(context)
        
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id, first_name, username, join_date, message_count 
                FROM users 
                WHERE join_date <= date('now', '-90 days')
                AND message_count < 5
                AND status != 'baneado'
            """) as cursor:
                rows = await cursor.fetchall()
                
        if not rows:
            return
            
        content = "Lista de usuarios inactivos (> 3 meses y < 5 mensajes)\n"
        content += "="*50 + "\n\n"
        for row in rows:
            content += f"ID: {row['user_id']} | Nombre: {row['first_name']} | User: @{row['username']} | Unió: {row['join_date']} | msjs: {row['message_count']}\n"
            
        f = io.BytesIO(content.encode('utf-8'))
        f.name = "inactivos_reporte.txt"
        
        try:
            await bot.send_document(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID if hasattr(config, 'ALERT_TOPIC_ID') else None,
                document=f,
                caption="🧹 **REPORTE DE PURGA MENSUAL**\n\nSe han detectado cuentas inactivas/fantasma con más de 3 meses de antigüedad y nula participación. Revisa el documento adjunto para eliminarlos si lo consideras necesario.",
                parse_mode='Markdown'
            )
        except Exception as e:
            pass
        try:
            os.makedirs(config.BACKUPS_DIR, exist_ok=True)
            filename = f"selene_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
            dest = os.path.join(config.BACKUPS_DIR, filename)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, db_manager.export_database_backup, dest)

            with open(dest, 'rb') as doc:
                await bot.send_document(
                    chat_id=config.ALERT_GROUP_ID,
                    message_thread_id=config.ALERT_TOPIC_ID,
                    document=doc,
                    filename=filename,
                    caption=f"💾 Respaldo de base de datos — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
            print("OK - Respaldo de BD enviado al grupo de alertas")
            return True, filename
        except Exception as e:
            print(f"Error enviando respaldo de BD: {e}")
            try:
                await bot.send_message(
                    chat_id=config.ALERT_GROUP_ID,
                    message_thread_id=config.ALERT_TOPIC_ID,
                    text=f"❌ Error generando respaldo de BD: {e}"
                )
            except Exception:
                pass
            return False, str(e)

    async def scan_broken_library_links(self, context):
        """Comprobar si los mensajes de respaldo siguen existiendo; borrar registros huérfanos."""
        from telegram.error import BadRequest, Forbidden
        bot = self._bot(context)
        records = await db_manager.get_library_backups_for_scan()
        removed = 0
        checked = 0
        for row in records:
            msg_id = row.get('backup_channel_msg_id')
            if not msg_id:
                continue
            checked += 1
            try:
                await bot.edit_message_reply_markup(
                    chat_id=config.BACKUP_GROUP_ID,
                    message_id=msg_id,
                    reply_markup=None
                )
            except BadRequest as e:
                err = str(e).lower()
                still_exists = (
                    'not modified' in err
                    or 'no reply markup' in err
                    or "message can't be edited" in err
                    or 'message is not modified' in err
                    or 'there is no text' in err
                    or "message can't be deleted" in err
                )
                missing = (
                    'not found' in err
                    or 'message to edit not found' in err
                    or 'message identifier is not specified' in err
                )
                if missing and not still_exists:
                    await db_manager.delete_library_backup(row['id'])
                    removed += 1
            except Forbidden:
                await db_manager.delete_library_backup(row['id'])
                removed += 1
            except Exception as e:
                print(f"Error comprobando backup {msg_id}: {e}")
            await asyncio.sleep(0.05)

        summary = (
            f"🔗 Escaneo de enlaces rotos\n"
            f"Revisados: {checked}\n"
            f"Eliminados de la BD: {removed}"
        )
        try:
            await bot.send_message(
                chat_id=config.ALERT_GROUP_ID,
                message_thread_id=config.ALERT_TOPIC_ID,
                text=summary
            )
        except Exception as e:
            print(f"Error enviando resumen de enlaces rotos: {e}")
        print(f"OK - {summary.replace(chr(10), ' | ')}")
        return checked, removed

    def is_silent_hours(self):
        """Devuelve True si es entre las 23:00 y las 07:00"""
        from datetime import datetime
        hour = datetime.now().hour
        return hour >= 23 or hour < 7

    async def daily_quote(self, context):
        """Enviar la frase literaria del día"""
        if self.is_silent_hours():
            return
            
        import json
        import os
        from datetime import datetime
        
        try:
            with open("data/frases.json", "r", encoding="utf-8") as f:
                frases = json.load(f)
            
            if not frases:
                return
                
            day_of_year = datetime.now().timetuple().tm_yday
            index = day_of_year % len(frases)
            frase = frases[index]
            
            msg = f"🌅 **Frase Literaria del Día**\n\n"
            msg += f"_{frase['text']}_\n\n"
            msg += f"— **{frase['author']}**, `{frase['book']}`"
            
            await context.bot.send_message(
                chat_id=config.GROUP_ID,
                text=msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error en daily_quote: {e}")

# Instancia global
scheduler_module = SchedulerModule()
