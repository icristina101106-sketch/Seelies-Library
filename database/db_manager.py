"""
Gestor de base de datos para Seelie
Maneja todas las operaciones CRUD
"""

import aiosqlite
from datetime import datetime, timedelta
import config
import json

class DatabaseManager:
    def __init__(self, db_path=config.DATABASE_PATH):
        self.db_path = db_path
    
    # ===== USUARIOS =====
    
    async def create_user(self, user_id, username=None, first_name=None, last_name=None, invited_by=None, has_photo=False):
        """Crear nuevo usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, invited_by, has_photo, status)
                VALUES (?, ?, ?, ?, ?, ?, 'nuevo')
            """, (user_id, username, first_name, last_name, invited_by, has_photo))
            await db.commit()
    
    async def get_user(self, user_id):
        """Obtener información de usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
                
    async def search_users_by_name(self, name: str):
        """Buscar usuarios por nombre parcial o exacto (Fase 5)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE first_name LIKE ?", (f"%{name}%",)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
    async def search_users_by_username(self, username: str):
        """Buscar usuarios por @username (Fase 5)"""
        username_clean = username.replace("@", "")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE username = ?", (username_clean,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def update_user_status(self, user_id, status):
        """Actualizar estado del usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
            await db.commit()
    
    async def update_user_photo_status(self, user_id, has_photo, deadline=None):
        """Actualizar estado de foto de perfil"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET has_photo = ?, photo_deadline = ?
                WHERE user_id = ?
            """, (has_photo, deadline, user_id))
            await db.commit()
    
    async def set_photo_reminder_sent(self, user_id):
        """Marcar que se envió recordatorio de foto"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET photo_reminder_sent = TRUE WHERE user_id = ?", (user_id,))
            await db.commit()
    
    async def promote_to_trusted(self, user_id):
        """Promover usuario a trusted"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET status = 'trusted', trusted_date = ?
                WHERE user_id = ?
            """, (datetime.now(), user_id))
            await db.commit()
    
    async def demote_from_trusted(self, user_id, reason):
        """Quitar estado trusted"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET status = 'normal', trusted_date = NULL, notes = ?
                WHERE user_id = ?
            """, (f"Trusted removido: {reason}", user_id))
            await db.commit()
    
    async def ban_user(self, user_id):
        """Marcar usuario como baneado"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET is_banned = TRUE, ban_date = ?
                WHERE user_id = ?
            """, (datetime.now(), user_id))
            await db.commit()
    
    # ===== WARNINGS =====
    
    async def get_member_quality_data(self, user_id: int) -> dict:
        """Obtener datos completos para el cálculo de calidad de miembro"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if not user:
                    return None
            
            async with db.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,)) as cursor:
                total_warnings = (await cursor.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM moderation_actions WHERE user_id = ? AND action_type IN ('mute', 'ban')", (user_id,)) as cursor:
                total_sanciones = (await cursor.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM moderation_actions WHERE user_id = ? AND action_type = 'untrust'", (user_id,)) as cursor:
                lost_trusted = (await cursor.fetchone())[0] > 0
                
            async with db.execute("SELECT COUNT(*) FROM user_reports WHERE reported_id = ? AND status = 'valido'", (user_id,)) as cursor:
                valid_reports = (await cursor.fetchone())[0]
                
            from datetime import datetime
            join_date = datetime.fromisoformat(user['join_date'])
            days_in_group = (datetime.now() - join_date).days
            
            return {
                'days_in_group': days_in_group,
                'total_warnings': total_warnings,
                'total_sanciones': total_sanciones,
                'lost_trusted': lost_trusted,
                'valid_reports': valid_reports,
                'risk_score': user['risk_score'],
                'status': user['status'],
                'is_banned': user['is_banned']
            }

    async def add_warning(self, user_id, warning_type, severity, message_text=None, message_id=None, chat_id=None, topic_id=None, action_taken=None):
        """Agregar warning a usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO warnings 
                (user_id, warning_type, severity, message_text, message_id, chat_id, topic_id, action_taken)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, warning_type, severity, message_text, message_id, chat_id, topic_id, action_taken))
            
            # Actualizar contador de warnings
            await db.execute("""
                UPDATE users 
                SET warnings_count = warnings_count + 1, last_warning_date = ?
                WHERE user_id = ?
            """, (datetime.now(), user_id))
            
            await db.commit()
    
    async def get_warning_count(self, user_id):
        """Obtener número de warnings de un usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM warnings 
                WHERE user_id = ? AND revoked = FALSE
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def revoke_warning(self, warning_id, admin_id):
        """Revocar una warning"""
        async with aiosqlite.connect(self.db_path) as db:
            # Obtener user_id de la warning
            async with db.execute("SELECT user_id FROM warnings WHERE id = ?", (warning_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_id = row[0]
                    
                    # Marcar warning como revocada
                    await db.execute("""
                        UPDATE warnings 
                        SET revoked = TRUE, revoked_by = ?, revoked_date = ?
                        WHERE id = ?
                    """, (admin_id, datetime.now(), warning_id))
                    
                    # Decrementar contador
                    await db.execute("""
                        UPDATE users 
                        SET warnings_count = warnings_count - 1
                        WHERE user_id = ?
                    """, (user_id,))
                    
                    await db.commit()
                    return True
            return False
    
    async def get_user_warnings(self, user_id, limit=10):
        """Obtener warnings de un usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM warnings 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def reset_trusted_warnings(self):
        """Resetear warnings de usuarios trusted (cada 2 semanas)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET warnings_count = 0
                WHERE status = 'trusted'
            """)
            await db.commit()
    
    # ===== RIESGO =====
    
    async def add_risk_event(self, user_id, event_type, risk_points, description=None):
        """Agregar evento de riesgo"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO risk_events (user_id, event_type, risk_points, description)
                VALUES (?, ?, ?, ?)
            """, (user_id, event_type, risk_points, description))
            
            # Actualizar score de riesgo
            await db.execute("""
                UPDATE users 
                SET risk_score = risk_score + ?, last_risk_update = ?
                WHERE user_id = ?
            """, (risk_points, datetime.now(), user_id))
            
            await db.commit()
    
    async def get_risk_score(self, user_id):
        """Obtener score de riesgo actual"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT risk_score FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def reduce_risk_over_time(self):
        """Reducir riesgo de usuarios trusted con el tiempo"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET risk_score = MAX(0, risk_score - 1)
                WHERE status = 'trusted' AND risk_score > 0
            """)
            await db.commit()
    
    async def set_risk_score(self, user_id, score):
        """Establecer score de riesgo manualmente"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET risk_score = ?, last_risk_update = ?
                WHERE user_id = ?
            """, (score, datetime.now(), user_id))
            await db.commit()
    
    # ===== ACCIONES DE MODERACIÓN =====
    
    async def log_moderation_action(self, user_id, action_type, reason=None, duration=None, message_deleted=None, message_id=None, chat_id=None, topic_id=None, auto_action=True, admin_id=None):
        """Registrar acción de moderación"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO moderation_actions 
                (user_id, action_type, reason, duration, message_deleted, message_id, chat_id, topic_id, auto_action, admin_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, action_type, reason, duration, message_deleted, message_id, chat_id, topic_id, auto_action, admin_id))
            await db.commit()
    
    async def get_user_history(self, user_id, limit=20):
        """Obtener historial de acciones de un usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM moderation_actions 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    # ===== PEDIDOS DE LIBROS =====
    
    async def create_book_request(self, user_id, title, author, language, format, request_method='privado'):
        """Crear solicitud de libro"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO book_requests (user_id, title, author, language, format, request_method)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, title, author, language, format, request_method))
            request_id = cursor.lastrowid
            await db.commit()
            return request_id
    
    async def update_request_message_id(self, request_id, message_id):
        """Actualizar ID del mensaje publicado"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE book_requests 
                SET message_id = ?
                WHERE id = ?
            """, (message_id, request_id))
            await db.commit()
    
    async def mark_request_completed(self, request_id):
        """Marcar pedido como atendido y programar auto-eliminación"""
        auto_delete_time = datetime.now() + timedelta(hours=config.REQUEST_AUTO_DELETE_HOURS)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE book_requests 
                SET status = 'atendido', completed_date = ?, auto_delete_scheduled = ?
                WHERE id = ?
            """, (datetime.now(), auto_delete_time, request_id))
            await db.commit()
        
        # Programar tarea de eliminación
        await self.schedule_task(
            task_type='delete_request',
            target_id=request_id,
            execute_at=auto_delete_time
        )
        
        return auto_delete_time
    
    async def get_request_by_message_id(self, message_id):
        """Obtener pedido por ID de mensaje"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM book_requests WHERE message_id = ? AND deleted = FALSE
            """, (message_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def mark_request_deleted(self, request_id: int):
        """Marcar un pedido como borrado (soft delete)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE book_requests SET deleted = TRUE, status = 'cancelado' WHERE id = ?", (request_id,))
            await db.commit()

    async def get_request(self, request_id: int):
        """Obtener pedido por ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM book_requests WHERE id = ?", (request_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def add_request_warning(self, request_id, user_id, warning_type, message):
        """Agregar warning por pedido incorrecto"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO request_warnings (request_id, user_id, warning_type, message)
                VALUES (?, ?, ?, ?)
            """, (request_id, user_id, warning_type, message))
            await db.commit()
    
    async def log_request_warning(self, request_id: int, user_id: int, warning_type: str):
        """Registrar que se dio un aviso a un usuario sobre su pedido"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO request_warnings (request_id, user_id, warning_type) VALUES (?, ?, ?)",
                (request_id, user_id, warning_type)
            )
            await db.commit()

    async def delete_library_item(self, message_id: int, topic_name: str):
        """Eliminar un registro de la biblioteca"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM library_backup WHERE message_id = ? AND topic_name = ?",
                (message_id, topic_name)
            )
            await db.commit()
            
    async def get_book_by_id(self, book_id: int):
        """Obtener un libro específico por su ID (Fase 4)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM library_backup WHERE id = ?", (book_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def add_to_waitlist(self, request_id: int, user_id: int):
        """Añadir usuario a la lista de espera de un pedido"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO request_waitlist (request_id, user_id) VALUES (?, ?)",
                    (request_id, user_id)
                )
                await db.commit()
            except Exception:
                pass

    async def get_waitlist_users(self, request_id: int):
        """Obtener todos los usuarios en la lista de espera de un pedido"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM request_waitlist WHERE request_id = ?", (request_id,)) as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]
    
    # ===== BACKUP DE BIBLIOTECA =====
    
    async def save_library_backup(self, topic_name, message_id, user_id, content_type, file_name=None, file_id=None, file_size=None, caption=None, text_content=None, backup_channel_msg_id=None, original_year=None, genre=None, page_count=None):
        """Guardar backup de mensaje de biblioteca"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO library_backup 
                (topic_name, message_id, user_id, content_type, file_name, file_id, file_size, caption, text_content, backup_channel_msg_id, original_year, genre, page_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (topic_name, message_id, user_id, content_type, file_name, file_id, file_size, caption, text_content, backup_channel_msg_id, original_year, genre, page_count))
            await db.commit()
    
    async def search_library_by_year(self, condition: str, year_val: int):
        """Busca libros basados en su año original (ej. '<= 1950')"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Prevenir inyección
            if condition not in ['<=', '>=', '=', '<', '>']:
                condition = '<='
            query = f"""
                SELECT id, file_name, topic_name, backup_channel_msg_id as message_id, '{config.BACKUP_GROUP_ID}' as chat_id
                FROM library_backup 
                WHERE original_year IS NOT NULL AND original_year {condition} ? 
                AND file_name IS NOT NULL
                ORDER BY original_year DESC
                LIMIT 50
            """
            async with db.execute(query, (year_val,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
    async def search_library_by_pages(self, condition: str, pages_val: int):
        """Busca libros basados en su número de páginas (ej. '< 200' o '> 500')"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if condition not in ['<=', '>=', '=', '<', '>']:
                condition = '<='
            query = f"""
                SELECT id, file_name, topic_name, backup_channel_msg_id as message_id, '{config.BACKUP_GROUP_ID}' as chat_id
                FROM library_backup 
                WHERE page_count IS NOT NULL AND page_count {condition} ? 
                AND file_name IS NOT NULL
                ORDER BY page_count DESC
                LIMIT 50
            """
            async with db.execute(query, (pages_val,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    async def search_library(self, query: str):
        """Busca en library_backup por file_name o caption usando MATCH o LIKE"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # LIKE simple
            like_query = f"%{query}%"
            async with db.execute("""
                SELECT id, file_name, topic_name, backup_channel_msg_id as message_id, ? as chat_id
                FROM library_backup
                WHERE (file_name LIKE ? OR caption LIKE ?) AND file_name IS NOT NULL
                ORDER BY timestamp DESC LIMIT 50
            """, (config.BACKUP_GROUP_ID, like_query, like_query)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    # ===== DUPLICADOS =====
    
    async def save_duplicate(self, file_name_1, file_name_2, message_id_1, message_id_2, similarity_score, match_type):
        """Guardar duplicado detectado"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO duplicate_files 
                (file_name_1, file_name_2, message_id_1, message_id_2, similarity_score, match_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_name_1, file_name_2, message_id_1, message_id_2, similarity_score, match_type))
            await db.commit()
    
    async def get_duplicates(self, reviewed=False):
        """Obtener duplicados no revisados"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM duplicate_files WHERE reviewed = ?
            """, (reviewed,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    # ===== TAREAS PROGRAMADAS =====
    
    async def schedule_task(self, task_type, execute_at, target_id=None, extra_data=None):
        """Programar tarea"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO scheduled_tasks (task_type, target_id, execute_at, extra_data)
                VALUES (?, ?, ?, ?)
            """, (task_type, target_id, execute_at, extra_data))
            await db.commit()
    
    async def cancel_pending_tasks(self, task_type, target_id):
        """Cancelar tareas pendientes de un tipo/objetivo"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE scheduled_tasks
                SET status = 'cancelled', completed_date = ?
                WHERE task_type = ? AND target_id = ? AND status = 'pending'
            """, (datetime.now(), task_type, target_id))
            await db.commit()
    
    async def get_pending_tasks(self):
        """Obtener tareas pendientes que deben ejecutarse"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM scheduled_tasks 
                WHERE status = 'pending' AND execute_at <= ?
            """, (datetime.now(),)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def complete_task(self, task_id):
        """Marcar tarea como completada"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE scheduled_tasks 
                SET status = 'completed', completed_date = ?
                WHERE id = ?
            """, (datetime.now(), task_id))
            await db.commit()
    
    async def schedule_message_deletion(self, message_id, chat_id, thread_id, delete_at, reason='manual'):
        """Programar borrado de mensaje específico"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO scheduled_tasks (task_type, target_id, execute_at, extra_data)
                VALUES (?, ?, ?, ?)
            """, ('delete_message', message_id, delete_at, json.dumps({
                'chat_id': chat_id,
                'thread_id': thread_id,
                'reason': reason
            })))
            await db.commit()
    
    # ===== AUDIT LOG =====
    
    async def add_audit_log(self, admin_id, admin_username, action_type, target_user_id=None, 
                          target_username=None, reason=None, details=None, chat_id=None, message_id=None):
        """Registrar acción en log de auditoría"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO audit_log 
                (admin_id, admin_username, action_type, target_user_id, target_username, 
                 reason, details, chat_id, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (admin_id, admin_username, action_type, target_user_id, target_username,
                  reason, details, chat_id, message_id))
            await db.commit()
    
    async def get_audit_log(self, admin_id=None, target_user_id=None, action_type=None, limit=20, offset=0):
        """Obtener log de auditoría con filtros opcionales"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []
            
            if admin_id:
                query += " AND admin_id = ?"
                params.append(admin_id)
            if target_user_id:
                query += " AND target_user_id = ?"
                params.append(target_user_id)
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_audit_log_count(self, admin_id=None, target_user_id=None, action_type=None):
        """Contar total de entradas en log de auditoría"""
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
            params = []
            
            if admin_id:
                query += " AND admin_id = ?"
                params.append(admin_id)
            if target_user_id:
                query += " AND target_user_id = ?"
                params.append(target_user_id)
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)
            
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    # ===== STATS =====
    
    async def get_stats(self):
        """Obtener estadísticas generales del grupo"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Total usuarios
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total_users = (await cursor.fetchone())[0]
            
            # Usuarios activos (no baneados)
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0") as cursor:
                active_users = (await cursor.fetchone())[0]
            
            # Trusted users
            async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'trusted'") as cursor:
                trusted_users = (await cursor.fetchone())[0]
            
            # Total pedidos
            async with db.execute("SELECT COUNT(*) FROM book_requests") as cursor:
                total_requests = (await cursor.fetchone())[0]
            
            # Pedidos pendientes
            async with db.execute("SELECT COUNT(*) FROM book_requests WHERE status = 'pendiente'") as cursor:
                pending_requests = (await cursor.fetchone())[0]
            
            # Pedidos atendidos
            async with db.execute("SELECT COUNT(*) FROM book_requests WHERE status = 'atendido'") as cursor:
                completed_requests = (await cursor.fetchone())[0]
            # Total warnings
            async with db.execute("SELECT COUNT(*) FROM warnings WHERE revoked = 0") as cursor:
                total_warnings = (await cursor.fetchone())[0]
            
            # Warnings esta semana
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            async with db.execute(
                "SELECT COUNT(*) FROM warnings WHERE timestamp > ? AND revoked = 0", 
                (week_ago,)
            ) as cursor:
                warnings_this_week = (await cursor.fetchone())[0]
            
            # Total baneos
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1") as cursor:
                total_bans = (await cursor.fetchone())[0]
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'trusted_users': trusted_users,
                'total_requests': total_requests,
                'pending_requests': pending_requests,
                'completed_requests': completed_requests,
                'total_warnings': total_warnings,
                'warnings_this_week': warnings_this_week,
                'total_bans': total_bans
            }
    
    # ===== PALABRAS PROHIBIDAS =====
    
    async def get_forbidden_words(self):
        """Obtener todas las palabras prohibidas activas"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM forbidden_words WHERE active = TRUE
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_top_requests_stats(self) -> dict:
        """Obtener estadísticas de los pedidos más solicitados"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            async with db.execute("""
                SELECT TRIM(LOWER(title)) as norm_title, COUNT(*) as count 
                FROM book_requests 
                GROUP BY norm_title 
                ORDER BY count DESC 
                LIMIT 10
            """) as cursor:
                top_books = [dict(row) for row in await cursor.fetchall()]
                
            async with db.execute("SELECT language, COUNT(*) as count FROM book_requests GROUP BY language ORDER BY count DESC") as cursor:
                lang_stats = [dict(row) for row in await cursor.fetchall()]
                
            async with db.execute("SELECT format, COUNT(*) as count FROM book_requests GROUP BY format ORDER BY count DESC") as cursor:
                format_stats = [dict(row) for row in await cursor.fetchall()]
                
            async with db.execute("SELECT COUNT(*) FROM book_requests WHERE published_date >= datetime('now', '-30 days')") as cursor:
                month_requests = (await cursor.fetchone())[0]
                
            return {
                'top_books': top_books,
                'lang_stats': lang_stats,
                'format_stats': format_stats,
                'month_requests': month_requests
            }

    async def get_weekly_report_data(self) -> dict:
        """Obtener datos para el reporte semanal"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Usuarios nuevos esta semana
            async with db.execute("SELECT COUNT(*) FROM users WHERE join_date >= datetime('now', '-7 days')") as cursor:
                new_members = (await cursor.fetchone())[0]
                
            # Usuarios sin foto
            async with db.execute("SELECT COUNT(*) FROM users WHERE has_photo = 0") as cursor:
                no_photo_users = (await cursor.fetchone())[0]
                
            # Nuevos trusted
            async with db.execute("SELECT COUNT(*) FROM moderation_actions WHERE action_type = 'trust' AND timestamp >= datetime('now', '-7 days')") as cursor:
                new_trusted = (await cursor.fetchone())[0]
                
            # Usuarios sospechosos
            async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'sospechoso'") as cursor:
                suspicious_users = (await cursor.fetchone())[0]
                
            # Warnings emitidas esta semana
            async with db.execute("SELECT COUNT(*) FROM warnings WHERE timestamp >= datetime('now', '-7 days')") as cursor:
                warnings_issued = (await cursor.fetchone())[0]
                
            # Warnings por tipo esta semana
            async with db.execute("""
                SELECT warning_type as type, COUNT(*) as count 
                FROM warnings 
                WHERE timestamp >= datetime('now', '-7 days') 
                GROUP BY warning_type
            """) as cursor:
                warnings_by_type = [dict(row) for row in await cursor.fetchall()]
                
            # Mutes y bans
            async with db.execute("SELECT COUNT(*) FROM moderation_actions WHERE action_type = 'mute' AND timestamp >= datetime('now', '-7 days')") as cursor:
                mutes = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM moderation_actions WHERE action_type = 'ban' AND timestamp >= datetime('now', '-7 days')") as cursor:
                bans = (await cursor.fetchone())[0]
                
            # Apelaciones
            async with db.execute("SELECT COUNT(*) FROM appeals WHERE created_date >= datetime('now', '-7 days')") as cursor:
                appeals = (await cursor.fetchone())[0]
                
            # Pedidos incorrectos
            async with db.execute("SELECT COUNT(*) FROM request_warnings WHERE timestamp >= datetime('now', '-7 days')") as cursor:
                incorrect_requests = (await cursor.fetchone())[0]
                
            # Duplicados detectados
            async with db.execute("SELECT COUNT(*) FROM duplicate_files WHERE timestamp >= datetime('now', '-7 days')") as cursor:
                duplicates = (await cursor.fetchone())[0]
                
            return {
                'new_members': new_members,
                'no_photo_users': no_photo_users,
                'new_trusted': new_trusted,
                'suspicious_users': suspicious_users,
                'warnings_issued': warnings_issued,
                'warnings_by_type': warnings_by_type,
                'mutes': mutes,
                'bans': bans,
                'appeals': appeals,
                'incorrect_requests': incorrect_requests,
                'duplicates': duplicates
            }
    async def save_learning_case(self, message_text: str, case_type: str, user_id: int, admin_decision: str = 'pending', context_data: str = None) -> int:
        """Guardar caso de aprendizaje en la base de datos"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO learning_cases (case_type, message_text, user_id, admin_decision, context)
                VALUES (?, ?, ?, ?, ?)
            """, (case_type, message_text, user_id, admin_decision, context_data))
            await db.commit()
            return cursor.lastrowid
            
    async def get_learning_case(self, case_id: int) -> dict:
        """Obtener un caso de aprendizaje por ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM learning_cases WHERE id = ?", (case_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
                
    async def update_learning_case(self, case_id: int, admin_decision: str):
        """Actualizar decisión de un caso de aprendizaje"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE learning_cases SET admin_decision = ? WHERE id = ?
            """, (admin_decision, case_id))
            await db.commit()

    async def save_appeal(self, user_id: int, appeal_type: str, reason: str, conversation: str = None) -> int:
        """Guardar una apelación"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO appeals (user_id, appeal_type, reason, conversation, status)
                VALUES (?, ?, ?, ?, 'pendiente')
            """, (user_id, appeal_type, reason, conversation))
            await db.commit()
            return cursor.lastrowid
            
    async def get_appeal(self, appeal_id: int) -> dict:
        """Obtener apelación por ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM appeals WHERE id = ?", (appeal_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
                
    async def update_appeal(self, appeal_id: int, status: str, admin_decision: str = None, admin_notes: str = None):
        """Actualizar estado de apelación"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE appeals 
                SET status = ?, admin_decision = ?, admin_notes = ?, resolved_date = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, admin_decision, admin_notes, appeal_id))
            await db.commit()

    async def get_pending_appeals(self) -> list:
        """Obtener todas las apelaciones pendientes"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM appeals WHERE status = 'pendiente' ORDER BY created_date ASC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def save_invite_link(self, link: str, creator_id: int):
        """Guardar un link de invitación único"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO invite_links (link, creator_id)
                VALUES (?, ?)
            """, (link, creator_id))
            await db.commit()
            
    async def get_invite_link_info(self, link: str) -> dict:
        """Obtener información de un link"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM invite_links WHERE link = ?", (link,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
                
    async def increment_invite_use(self, link: str):
        """Incrementar contador de usos de un link"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE invite_links SET uses = uses + 1 WHERE link = ?", (link,))
            await db.commit()
            
    async def get_user_invite_links(self, user_id: int) -> list:
        """Obtener links creados por un usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM invite_links WHERE creator_id = ? ORDER BY created_date DESC", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def search_library(self, query: str) -> list:
        """Buscar libros en la biblioteca por título o autor"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            search_term = f"%{query}%"
            async with db.execute("""
                SELECT file_name, message_id, topic_name, chat_id, timestamp
                FROM library_backup 
                WHERE LOWER(file_name) LIKE LOWER(?) 
                ORDER BY timestamp DESC 
                LIMIT 20
            """, (search_term,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def search_library_by_genre(self, genre: str):
        """Busca libros basados en su genero"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = f"""
                SELECT id, file_name, topic_name, backup_channel_msg_id as message_id, '{config.BACKUP_GROUP_ID}' as chat_id
                FROM library_backup 
                WHERE genre IS NOT NULL AND genre LIKE ?
                ORDER BY id DESC LIMIT 50
            """
            async with db.execute(query, (f"%{genre}%",)) as cursor:
                results = await cursor.fetchall()
                return [dict(r) for r in results]
                
    async def get_all_genres(self):
        """Obtener la lista de todos los generos unicos"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT DISTINCT genre FROM library_backup WHERE genre IS NOT NULL AND genre != 'Desconocido' ORDER BY genre") as cursor:
                results = await cursor.fetchall()
                return [r[0] for r in results]

    async def get_recommendations(self, user_id: int):
        """Generar recomendaciones basadas en los pedidos previos del usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Obtener autores de los pedidos del usuario
            async with db.execute("SELECT DISTINCT author FROM book_requests WHERE user_id = ? AND author != '' AND author IS NOT NULL LIMIT 5", (user_id,)) as cursor:
                authors = [r[0] for r in await cursor.fetchall()]
                
            if not authors:
                return []
                
            # Buscar en library_backup por esos autores
            results = []
            for author in authors:
                query = f"""
                    SELECT id, file_name, topic_name, backup_channel_msg_id as message_id, '{config.BACKUP_GROUP_ID}' as chat_id
                    FROM library_backup 
                    WHERE LOWER(file_name) LIKE LOWER(?) OR LOWER(caption) LIKE LOWER(?)
                    ORDER BY id DESC LIMIT 5
                """
                async with db.execute(query, (f"%{author}%", f"%{author}%")) as cursor:
                    rows = await cursor.fetchall()
                    results.extend([dict(r) for r in rows])
                    
            # Eliminar duplicados usando 'id'
            unique_results = []
            seen_ids = set()
            for r in results:
                if r['id'] not in seen_ids:
                    seen_ids.add(r['id'])
                    unique_results.append(r)
                    
            return unique_results[:15]

    async def get_setting(self, key: str, default=None):
        """Obtener valor de configuración"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT setting_value FROM bot_settings WHERE setting_key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default
                
    async def set_setting(self, key: str, value: str, admin_id: int = None):
        """Guardar valor de configuración y registrar cambio"""
        async with aiosqlite.connect(self.db_path) as db:
            # Obtener valor anterior
            async with db.execute("SELECT setting_value FROM bot_settings WHERE setting_key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                old_value = row[0] if row else None
                
            await db.execute("INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)", (key, str(value)))
            
            # Registrar en log
            if admin_id and old_value != str(value):
                await db.execute(
                    "INSERT INTO config_log (admin_id, setting_key, old_value, new_value) VALUES (?, ?, ?, ?)",
                    (admin_id, key, old_value, str(value))
                )
            await db.commit()

    async def get_config_log(self, limit: int = 10):
        """Obtener historial de cambios de configuración"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM config_log ORDER BY timestamp DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def add_forbidden_book(self, title: str, reason: str, added_by: int):
        """Añadir libro a la lista negra"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO forbidden_books (title, reason, added_by) VALUES (?, ?, ?)", (title, reason, added_by))
            await db.commit()
            
    async def remove_forbidden_book(self, title: str):
        """Eliminar libro de la lista negra"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM forbidden_books WHERE LOWER(title) = LOWER(?)", (title,))
            await db.commit()
            
    async def get_forbidden_book_reason(self, title: str):
        """Revisar si un libro está prohibido, retornar razón si lo está"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT reason FROM forbidden_books WHERE LOWER(?) LIKE '%' || LOWER(title) || '%'", (title,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def increment_download(self, book_id: int):
        """Incrementar contador de descargas de un libro"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE library_backup SET forwards_count = COALESCE(forwards_count, 0) + 1 WHERE id = ?", (book_id,))
            await db.commit()
            
    async def get_most_read(self, limit: int = 10):
        """Obtener libros más descargados/leídos"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = f"""
                SELECT id, file_name, topic_name, backup_channel_msg_id as message_id, '{config.BACKUP_GROUP_ID}' as chat_id, COALESCE(forwards_count, 0) as downloads
                FROM library_backup 
                WHERE forwards_count > 0
                ORDER BY forwards_count DESC, timestamp DESC
                LIMIT ?
            """
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_pending_requests_matching(self, filename: str) -> list:
        """Buscar pedidos pendientes que coincidan con un nombre de archivo"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            search_term = f"%{filename}%"
            async with db.execute("""
                SELECT id, user_id, title, author, language, format, status, message_id
                FROM book_requests 
                WHERE status = 'pendiente' AND LOWER(title) LIKE LOWER(?)
                ORDER BY published_date DESC
            """, (search_term,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
    async def get_old_pending_requests(self, days: int = 15) -> list:
        """Obtener pedidos pendientes que tienen más de X días"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = f"""
                SELECT id, user_id, title, author, published_date, message_id
                FROM book_requests 
                WHERE status = 'pendiente' AND deleted = FALSE 
                AND published_date < datetime('now', '-{days} days')
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_user_requests(self, user_id: int) -> list:
        """Obtener todos los pedidos de un usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT id, title, author, status, published_date, completed_date
                FROM book_requests 
                WHERE user_id = ? AND deleted = FALSE
                ORDER BY published_date DESC
            """
            async with db.execute(query, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_user_favorite_genre(self, user_id: int):
        """Obtener el género más aportado por el usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT genre, COUNT(*) as c 
                FROM library_backup 
                WHERE user_id = ? AND genre IS NOT NULL AND genre != 'Desconocido'
                GROUP BY genre 
                ORDER BY c DESC 
                LIMIT 1
            """
            async with db.execute(query, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else "Desconocido"

    async def get_all_library_items(self):
        """Obtener todos los libros de la biblioteca para exportar"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT l.file_name, l.genre, l.original_year, l.page_count, l.timestamp, u.username, u.first_name
                FROM library_backup l
                LEFT JOIN users u ON l.user_id = u.user_id
                ORDER BY l.timestamp DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
    async def get_all_pending_requests(self):
        """Obtener todos los pedidos pendientes ordenados por antigüedad"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM book_requests
                WHERE status = 'pendiente' AND deleted = FALSE
                ORDER BY published_date ASC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_group_statistics(self):
        """Obtener estadísticas generales del grupo"""
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            # Total de libros
            async with db.execute("SELECT COUNT(*) FROM library_backup") as cursor:
                stats['total_books'] = (await cursor.fetchone())[0]
            
            # Pedidos atendidos este mes
            async with db.execute("SELECT COUNT(*) FROM book_requests WHERE status = 'atendido' AND completed_date >= date('now', '-30 days')") as cursor:
                stats['requests_month'] = (await cursor.fetchone())[0]
                
            # Género más popular
            async with db.execute("SELECT genre FROM library_backup WHERE genre IS NOT NULL AND genre != 'Desconocido' GROUP BY genre ORDER BY COUNT(*) DESC LIMIT 1") as cursor:
                row = await cursor.fetchone()
                stats['top_genre'] = row[0] if row else "N/A"
                
            # Aportador del mes
            async with db.execute("""
                SELECT u.first_name, COUNT(l.id) as c 
                FROM library_backup l
                JOIN users u ON l.user_id = u.user_id
                WHERE l.timestamp >= datetime('now', '-30 days')
                GROUP BY l.user_id 
                ORDER BY c DESC LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                stats['top_contributor'] = row[0] if row else "N/A"
                
            return stats

    async def increment_user_contributions(self, user_id: int):
        """Incrementar el contador de aportes de un usuario y actualizar su rango"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("UPDATE users SET contributions = COALESCE(contributions, 0) + 1 WHERE user_id = ?", (user_id,))
            
            # Obtener aportes actuales
            async with db.execute("SELECT contributions, rank FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    contribs = row['contributions']
                    old_rank = row['rank'] or 0
                    
                    # Calcular nuevo rango
                    new_rank = 0
                    if contribs >= 50: new_rank = 4 # Guardian
                    elif contribs >= 21: new_rank = 3 # Aportador Estrella
                    elif contribs >= 6: new_rank = 2 # Aportador
                    elif contribs >= 1: new_rank = 1 # Colaborador
                    
                    if new_rank > old_rank:
                        await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (new_rank, user_id))
                        await db.commit()
                        return new_rank # Retornar el nuevo rango para felicitar
            
            await db.commit()
            return None

    async def increment_message_count(self, user_id: int):
        """Incrementar contador de mensajes"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET message_count = COALESCE(message_count, 0) + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_top_contributors(self, limit: int = 10) -> list:
        """Obtener top aportadores"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id, username, first_name, contributions, rank 
                FROM users 
                WHERE contributions > 0 
                ORDER BY contributions DESC 
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_request_status(self, request_id: int, status: str):
        """Actualizar estado de un pedido"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE book_requests SET status = ? WHERE id = ?",
                (status, request_id)
            )
            await db.commit()

    # ===== ADMISIÓN =====

    async def get_banned_user_names(self):
        """Obtener nombres de usuarios baneados"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT first_name FROM users WHERE status = 'baneado'") as cursor:
                rows = await cursor.fetchall()
                return [r[0].lower() for r in rows if r[0]]

    async def get_banned_user_messages(self):
        """Obtener textos de mensajes de usuarios baneados"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT w.message_text 
                FROM warnings w
                JOIN users u ON w.user_id = u.user_id
                WHERE u.status = 'baneado' AND w.message_text IS NOT NULL
            """) as cursor:
                rows = await cursor.fetchall()
                return [r[0].lower() for r in rows if len(r[0]) > 10]

    async def get_user_uploads(self, user_id: int):
        """Obtener los libros subidos por un usuario"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT file_name, timestamp, genre, page_count 
                FROM library_backup 
                WHERE user_id = ? AND file_name IS NOT NULL
                ORDER BY timestamp DESC
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def save_join_request(self, user_id: int, chat_id: int):
        """Guardar o renovar una solicitud de unión pendiente"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO join_requests (user_id, chat_id, status, requested_at)
                VALUES (?, ?, 'pending', ?)
                ON CONFLICT(user_id, chat_id) DO UPDATE SET
                    status = 'pending',
                    requested_at = excluded.requested_at
            """, (user_id, chat_id, datetime.now()))
            await db.commit()

    async def get_join_request(self, user_id: int, chat_id: int):
        """Obtener solicitud de unión"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM join_requests WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_join_request_status(self, user_id: int, chat_id: int, status: str):
        """Actualizar estado de solicitud de unión"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE join_requests SET status = ? WHERE user_id = ? AND chat_id = ?",
                (status, user_id, chat_id)
            )
            await db.commit()

    async def get_all_authors(self):
        """Obtiene una lista de autores únicos extrayéndolos de los nombres de archivo"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT file_name FROM library_backup") as cursor:
                rows = await cursor.fetchall()
        
        authors = set()
        for row in rows:
            fname = row['file_name']
            if not fname: continue
            # Buscar el patrón "Título - Autor.ext" o similar
            import re
            clean = re.sub(r'\.\w+$', '', fname)
            parts = clean.split(' - ')
            if len(parts) >= 2:
                author = parts[-1].strip()
                if len(author) > 2 and len(author) < 50:
                    authors.add(author)
                    
        return sorted(list(authors))
        
    async def get_books_by_author(self, author: str):
        """Obtiene libros de un autor específico"""
        return await self.search_library(author)

    # ===== MANTENIMIENTO BIBLIOTECA / BD =====

    async def get_library_backups_for_scan(self):
        """Obtener registros de biblioteca con mensaje de respaldo"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT id, file_name, backup_channel_msg_id, topic_name
                FROM library_backup
                WHERE backup_channel_msg_id IS NOT NULL
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def delete_library_backup(self, backup_id: int):
        """Eliminar un registro de library_backup"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM library_backup WHERE id = ?", (backup_id,))
            await db.commit()

    def export_database_backup(self, dest_path: str) -> str:
        """Copiar la BD a dest_path con el API de backup de SQLite."""
        import os
        import sqlite3
        os.makedirs(os.path.dirname(dest_path) or '.', exist_ok=True)
        src = sqlite3.connect(self.db_path)
        dst = sqlite3.connect(dest_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return dest_path

# Instancia global
db_manager = DatabaseManager()
