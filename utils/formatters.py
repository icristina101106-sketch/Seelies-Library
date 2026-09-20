"""
Formateadores de mensajes para Seelie
Genera mensajes bonitos y estructurados
"""

from datetime import datetime
import config

class MessageFormatter:
    
    @staticmethod
    def format_alert(user_id, username, user_status, motivo, mensaje_texto, accion, warnings_count, risk_score):
        """Formatear alerta para el canal de alertas"""
        alert = "🚨 ALERTA SEELIE\n"
        alert += "=" * 40 + "\n\n"
        
        alert += f"👤 Usuario: {username if username else 'sin username'}\n"
        alert += f"   ID: {user_id}\n"
        alert += f"   Estado: {user_status}\n\n"
        
        alert += f"⚠️ Motivo: {motivo}\n\n"
        
        if mensaje_texto:
            preview = mensaje_texto[:100] + "..." if len(mensaje_texto) > 100 else mensaje_texto
            alert += f"💬 Mensaje:\n{preview}\n\n"
        
        alert += f"⚡ Acción aplicada: {accion}\n"
        alert += f"📊 Warnings: {warnings_count}/{config.MAX_WARNINGS_BEFORE_BAN}\n"
        alert += f"🎯 Riesgo: {risk_score}/{config.RISK_SCORE_BAN_THRESHOLD}\n\n"
        
        alert += f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return alert
    
    @staticmethod
    def format_warning_message(warning_type, severity, show_reason=True):
        """Formatear mensaje de advertencia al usuario"""
        messages = {
            'link': "Enlace eliminado. Revisa las normas del grupo.",
            'spam': "Evita hacer spam.",
            'flood': "Evita el flood de mensajes.",
            'palabra_leve': "Cuida tu lenguaje.",
            'palabra_media': "Se aplicó una advertencia. Revisa las normas del grupo.",
            'palabra_grave': "Has sido expulsado por lenguaje inapropiado.",
            'repeticion': "Evita repetir mensajes.",
            'archivo_sospechoso': "Archivo no permitido.",
            'invitacion': "No se permiten invitaciones a otros grupos.",
            'reenvio_masivo': "Evita reenviar mensajes masivamente.",
        }
        
        base_message = messages.get(warning_type, "Mensaje eliminado. Revisa las normas del grupo.")
        
        if show_reason and config.SHOW_REASON_IN_MESSAGES:
            return f"{base_message}\nMotivo: {warning_type}"
        
        return base_message
    
    @staticmethod
    def format_mute_message(duration_minutes):
        """Formatear mensaje de mute"""
        if duration_minutes < 60:
            time_str = f"{duration_minutes} minutos"
        else:
            hours = duration_minutes // 60
            time_str = f"{hours} hora{'s' if hours > 1 else ''}"
        
        return f"Se aplicó una restricción temporal de {time_str}."
    
    @staticmethod
    def format_ban_message():
        """Formatear mensaje de ban"""
        return "El usuario ha sido removido por incumplimiento grave."
    
    @staticmethod
    def format_photo_warning(username, hours_left):
        """Formatear aviso de foto faltante"""
        display = f"@{username}" if username else "Usuario"
        return f"{display}\n\nTienes {hours_left} horas para actualizar tu foto de perfil a pública.\nLa foto debe ser una imagen real, no un símbolo, letra o signo.\n\nSi no actualizas tu foto en el tiempo indicado, serás removido del grupo."
    
    @staticmethod
    def format_photo_reminder(username):
        """Formatear recordatorio de foto"""
        message = f"{username if username else 'Usuario'}\n\n"
        message += "⏰ Recordatorio: Te quedan 12 horas para actualizar tu foto de perfil.\n\n"
        message += "Este es tu último aviso antes de ser removido del grupo."
        return message
    
    @staticmethod
    def format_welcome_message(username, first_name=None, group_name=None):
        """Formatear mensaje de bienvenida para #general - mensajes aleatorios"""
        import random
        import config
        
        # Si no hay username, usar el nombre
        display_name = f"@{username}" if username else (first_name or "Nueva miembro")
        group = group_name or config.GROUP_NAME
        
        # 20 Plantillas originales únicas (no copia de la imagen ejemplo)
        templates = [
            f"✨ Tu energía llegó suavecita a {group}...\n{display_name}, bienvenid@. Espero que encuentres lo que buscas y te quedes un rato. 🌙",
            
            f"🌸 Alguien nuevo pisó este espacio...\n{display_name}, bienvenid@ a {group}. Que tu paso sea ligero y tu estancia agradable. ✨",
            
            f"📖 Las páginas de {group} se volvieron a abrir...\n{display_name}, bienvenid@. Respira hondo y siéntete en casa. 🕊️",
            
            f"🦋 Un nuevo capítulo comienza en {group}...\n{display_name}, bienvenid@. Que encuentres historias que te acompañen. 💫",
            
            f"🌿 El viento trajo una visita a {group}...\n{display_name}, bienvenid@. Ojalá este lugar te guste tanto como a nosotros. ☁️",
            
            f"⭐ Entre libros y café imaginario en {group}...\n{display_name}, bienvenid@. Siéntate, relájate, disfruta. 📚",
            
            f"🌙 Se sintió tu presencia discreta en {group}...\n{display_name}, bienvenid@. Que aquí encuentres paz y buenas lecturas. 🍃",
            
            f"💫 Otro alma curiosa llegó a {group}...\n{display_name}, bienvenid@. Espero que este espacio te abrace. 🌺",
            
            f"🌷 {group} tiene una nueva historia por contar...\n{display_name}, bienvenid@. Que tu visita sea memorable. 📖",
            
            f"☁️ Una nube de curiosidad flotó hasta {group}...\n{display_name}, bienvenid@. Siente el ambiente, quédate un rato. 🌸",
            
            f"🕯️ La luz de una nueva vela encendió {group}...\n{display_name}, bienvenid@. Que encuentres calidez aquí. ✨",
            
            f"🍃 {group} se hace más grande contigo...\n{display_name}, bienvenid@. Un nuevo rincón espera por ti. 🌿",
            
            f"📚 Las estanterías de {group} te reciben...\n{display_name}, bienvenid@. Cada libro es una puerta nueva. 🚪",
            
            f"🌌 Universo de historias en {group}...\n{display_name}, bienvenid@. Que encuentres tu próxima aventura. ⭐",
            
            f"🦋 {group} expande sus alas...\n{display_name}, bienvenid@. Vuela libre entre estas páginas. 🌙",
            
            f"☕ Silencio y aroma de libros en {group}...\n{display_name}, bienvenid@. El mejor lugar para perderse y encontrarse. 📖",
            
            f"🌸 {group} florece con tu llegada...\n{display_name}, bienvenid@. Que encuentres belleza en cada página. 🌷",
            
            f"💭 Pensamientos y letras en {group}...\n{display_name}, bienvenid@. Tu mente encontrará refugio aquí. 🌿",
            
            f"🌟 Magia en cada esquina de {group}...\n{display_name}, bienvenid@. Que la lectura te transforme. ✨",
            
            f"🕊️ {group} te abre sus puertas...\n{display_name}, bienvenid@. Entra con calma, quédate con gusto. 📚",
        ]
        
        return random.choice(templates)
    
    @staticmethod
    def get_welcome_image_path():
        """Obtener ruta de imagen de bienvenida aleatoria
        
        Para usar imágenes:
        1. Guarda imágenes en: assets/welcome_images/
        2. Nombra: welcome_1.jpg, welcome_2.jpg, etc.
        3. El bot seleccionará una aleatoriamente
        
        Ejemplo de uso en users.py:
        
            image_path = formatter.get_welcome_image_path()
            if image_path:
                await context.bot.send_photo(
                    chat_id=config.GROUP_ID,
                    photo=open(image_path, 'rb'),
                    caption=welcome_msg
                )
            else:
                await context.bot.send_message(...)
        
        """
        import os
        import random
        import json
        import config
        
        welcome_dir = config.WELCOME_IMAGES_DIR
        
        if not os.path.exists(welcome_dir):
            return None
        
        # Buscar imágenes (jpg, jpeg, png, webp)
        valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        images = [f for f in os.listdir(welcome_dir) 
                  if f.lower().endswith(valid_extensions)]
        
        if not images:
            return None
            
        # Shuffle System
        shuffle_file = 'data/shuffle_state.json'
        pool = []
        if os.path.exists(shuffle_file):
            try:
                with open(shuffle_file, 'r') as f:
                    pool = json.load(f)
            except:
                pass
                
        # Filtrar solo imágenes que aún existen
        pool = [img for img in pool if img in images]
        
        # Si el pool está vacío, lo llenamos con todas las imágenes y mezclamos
        if not pool:
            pool = list(images)
            random.shuffle(pool)
            
        # Tomar la primera imagen del pool
        selected = pool.pop(0)
        
        # Guardar el pool restante
        os.makedirs('data', exist_ok=True)
        with open(shuffle_file, 'w') as f:
            json.dump(pool, f)
            
        return os.path.join(welcome_dir, selected)
    
    @staticmethod
    def format_request_published(title, author, language, format, username, tipo='standalone'):
        """Formatear pedido publicado en #peticiones"""
        # Determinar emoji según tipo
        tipo_emojis = {
            'standalone': '📖',
            'duología': '📚',
            'trilogía': '📚📚',
            'saga': '📚📚📚'
        }
        tipo_emoji = tipo_emojis.get(tipo, '📖')
        
        # Formatear título según tipo
        if tipo == 'standalone':
            titulo_label = "Título"
        elif tipo == 'duología':
            titulo_label = "Títulos (Duología)"
        elif tipo == 'trilogía':
            titulo_label = "Títulos (Trilogía)"
        else:
            titulo_label = "Títulos (Saga)"
        
        # Formatear múltiples títulos con numeración
        import re
        titulos_lista = [t.strip() for t in re.split(r'[,\n]+', title) if t.strip()]
        if len(titulos_lista) > 1:
            titulo_formateado = '\n'.join([f"   {i+1}. {t}" for i, t in enumerate(titulos_lista)])
        else:
            titulo_formateado = title
        
        message = f"{tipo_emoji} Nueva petición\n"
        message += "=" * 30 + "\n\n"
        message += f"📖 {titulo_label}:\n{titulo_formateado}\n\n"
        message += f"✍️ Autor: {author}\n"
        message += f"🌐 Idioma: {language}\n"
        message += f"📄 Formato: {format}\n\n"
        message += f"Solicitado por: @{username}"
        return message
    
    @staticmethod
    def format_request_ready_notification(username):
        """Formatear notificación de pedido listo"""
        message = f"@{username}\n\n"
        message += "✅ Tu pedido ya está disponible en la biblioteca.\n"
        message += "Te invito a revisarlo y disfrutar de tu lectura.\n\n"
        message += "Cuando veas este mensaje, elimina tu petición.\n"
        message += "Si no lo haces, será eliminada automáticamente en 24 horas."
        return message
    
    @staticmethod
    def format_request_incorrect_message(warning_type):
        """Formatear mensaje educativo de pedido incorrecto"""
        messages = {
            'incompleto': "Tu solicitud está incompleta. Revisa el formato antes de volver a publicar.",
            'fuera_formato': "Tu solicitud no sigue el formato establecido. Corrígela y vuelve a intentarlo.",
            'repetido': "Tu solicitud ya existe o fue publicada de forma repetida. Revisa antes de volver a pedirlo.",
            'incorrecto': "Tu solicitud tiene errores. Por favor revisa el formato correcto."
        }
        return messages.get(warning_type, messages['incorrecto'])
    
    @staticmethod
    def format_checkuser_info(user_data, warnings, risk_events, actions, quality_data=None):
        """Formatear información completa de usuario para /checkuser"""
        info = "👤 INFORMACIÓN DE USUARIO\n"
        info += "=" * 50 + "\n\n"
        
        info += f"ID: {user_data['user_id']}\n"
        info += f"Username: @{user_data['username'] if user_data['username'] else 'sin username'}\n"
        info += f"Nombre: {user_data['first_name']}\n"
        info += f"Estado: {user_data['status']}\n"
        
        # Fecha de registro en el bot
        join_date = datetime.fromisoformat(user_data['join_date'])
        info += f"Registrado desde: {join_date.strftime('%d/%m/%Y')}\n"
        
        # Foto
        info += f"Foto de perfil: {'✅ Sí' if user_data['has_photo'] else '❌ No'}\n"
        
        # Trusted
        if user_data['trusted_date']:
            info += f"Trusted: ✅ Desde {user_data['trusted_date'][:10]}\n"
        else:
            info += "Trusted: ❌ No\n"
        
        info += f"\n📊 ESTADÍSTICAS\n"
        
        # Gamificación y Actividad
        ranks = {0: "Lector", 1: "Colaborador", 2: "Aportador", 3: "Aportador Estrella", 4: "Guardián"}
        user_rank = user_data.get('rank', 0) or 0
        info += f"Rango: {ranks.get(user_rank, 'Lector')}\n"
        info += f"Mensajes enviados: {user_data.get('message_count', 0)}\n"
        info += f"Libros aportados: {user_data.get('contributions', 0)}\n\n"
        
        info += f"Warnings: {user_data['warnings_count']}/{config.MAX_WARNINGS_BEFORE_BAN}\n"
        info += f"Riesgo: {user_data['risk_score']}/{config.RISK_SCORE_BAN_THRESHOLD}\n"
        
        # Últimas warnings
        if warnings:
            info += f"\n⚠️ ÚLTIMAS WARNINGS ({len(warnings)})\n"
            for w in warnings[:5]:
                info += f"  • {w['warning_type']} ({w['severity']}) - {w['timestamp'][:10]}\n"
        
        # Calidad de miembro
        quality = MessageFormatter._calculate_member_quality(quality_data)
        info += f"\n🎯 Calidad de miembro: {quality}\n"
        
        return info
    
    @staticmethod
    def _calculate_member_quality(quality_data: dict):
        """Calcular calidad de miembro usando un sistema de scoring"""
        if not quality_data:
            return "➖ Desconocida"
            
        if quality_data['is_banned']:
            return "❌ Baneado"
            
        score = 100
        score -= (quality_data['total_warnings'] * 10)
        score -= (quality_data['total_sanciones'] * 15)
        score -= (quality_data['risk_score'] * 2)
        if quality_data['lost_trusted']:
            score -= 30
            
        # Bonificaciones
        score += min(quality_data['days_in_group'], 180) / 6  # max +30
        if quality_data['status'] == 'trusted':
            score += 10
            
        if score >= 85:
            return "⭐ Excelente"
        elif score >= 65:
            return "✅ Estable"
        elif score >= 45:
            return "➖ Observado"
        elif score >= 25:
            return "⚠️ Riesgoso"
        else:
            return "🚨 Problemático"

    
    @staticmethod
    def format_duplicate_report(duplicates):
        """Formatear reporte de duplicados"""
        if not duplicates:
            return "✅ No se encontraron duplicados."
        
        report = "📋 DUPLICADOS DETECTADOS\n"
        report += "=" * 50 + "\n\n"
        
        for i, dup in enumerate(duplicates, 1):
            report += f"{i}. \"{dup['file_name_1']}\"\n"
            report += f"   Mensaje {dup['message_id_1']} y {dup['message_id_2']}\n"
            report += f"   Similitud: {int(dup['similarity_score'] * 100)}% ({dup['match_type']})\n\n"
        
        report += f"Total: {len(duplicates)} duplicados encontrados\n"
        return report
    
    @staticmethod
    def format_test_mode_message(action):
        """Formatear mensaje de modo prueba"""
        return f"[MODO PRUEBA] Acción que se habría tomado: {action}"

# Instancia global
formatter = MessageFormatter()
