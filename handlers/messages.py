"""
Handler de Mensajes
Procesa todos los mensajes del grupo
"""

from telegram import Update
from telegram.ext import ContextTypes
import config
from database.db_manager import db_manager
from modules.moderation import moderation_module
from modules.risk import risk_module
from modules.warnings import warnings_module

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes privados (Reenvíos mortales y OCR)"""
    message = update.message
    if not message or not message.from_user:
        return
        
    user_id = message.from_user.id
    if user_id not in config.ADMIN_IDS:
        return # Solo admins pueden usar esto
        
    # 1. Reenvío Mortal
    if message.forward_origin:
        target_user = None
        target_name = None
        
        if message.forward_origin.type == 'user':
            target_user = message.forward_origin.sender_user.id
            target_name = message.forward_origin.sender_user.first_name
        elif message.forward_origin.type == 'hidden_user':
            target_name = message.forward_origin.sender_user_name
            # Buscar en DB por nombre
            users = await db_manager.search_users_by_name(target_name)
            if users and len(users) == 1:
                target_user = users[0]['user_id']
                
        if target_user:
            try:
                await context.bot.ban_chat_member(chat_id=config.GROUP_ID, user_id=target_user)
                await db_manager.update_user_status(target_user, 'baneado')
                await message.reply_text(f"✅ **Reenvío Mortal Exitoso:**\nEl usuario {target_name} ({target_user}) ha sido BANEADO del grupo.")
            except Exception as e:
                await message.reply_text(f"❌ Error al banear: {e}")
        else:
            await message.reply_text(f"❌ No pude identificar el ID del usuario (Privacidad activa). Nombre: {target_name}")
        return
        
    # 2. Captura de Pantalla OCR
    if message.photo:
        status = await message.reply_text("🔍 Escaneando imagen con Inteligencia Artificial (OCR)...")
        try:
            import tempfile
            import os
            from PIL import Image
            import pytesseract
            
            photo_file = await context.bot.get_file(message.photo[-1].file_id)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            tmp.close()
            await photo_file.download_to_drive(tmp.name)
            
            text = pytesseract.image_to_string(Image.open(tmp.name))
            os.unlink(tmp.name)
            
            import re
            match = re.search(r'@(\w+)', text)
            if match:
                username = match.group(1)
                users = await db_manager.search_users_by_username(username)
                if users:
                    target = users[0]
                    await context.bot.ban_chat_member(chat_id=config.GROUP_ID, user_id=target['user_id'])
                    await db_manager.update_user_status(target['user_id'], 'baneado')
                    await status.edit_text(f"🎯 **¡Blanco fijado! (OCR)**\nEncontré el usuario @{username} (ID: {target['user_id']}) en la imagen.\n✅ Ha sido BANEADO exitosamente.")
                else:
                    await status.edit_text(f"⚠️ Encontré a @{username} en la imagen, pero no está en mi BD.")
            else:
                await status.edit_text("❌ No encontré ningún `@usuario` en la imagen.")
        except Exception as e:
            await status.edit_text(f"❌ Error en OCR: {e}")
        return

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes del grupo"""
    message = update.message
    if not message or not message.from_user:
        return
    
    user_id = message.from_user.id
    
    # Ignorar mensajes del bot mismo
    if user_id == context.bot.id:
        return
        
    from modules import toggles
    
    # Verificar si es un archivo (Biblioteca)
    if message.document:
        if not toggles.is_enabled("biblioteca"):
            return
        # Solo procesar PDF y EPUB
        file_name = message.document.file_name.lower()
        if file_name.endswith('.pdf') or file_name.endswith('.epub'):
            # Ignorar si viene del admin en modo mantenimiento
            if user_id in config.ADMIN_IDS:
                # Los admins siempre pueden subir
                pass
            from modules.library import library_module
            await library_module.handle_upload(update, context)
        return
        
    if not toggles.is_enabled("moderacion"):
        return
    
    # Obtener o crear usuario
    user_data = await db_manager.get_user(user_id)
    if not user_data:
        # Crear usuario si no existe
        await db_manager.create_user(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        user_data = await db_manager.get_user(user_id)
        
    await db_manager.increment_message_count(user_id)
        
    # Validar que tiene fotos y nombre, etc. (se asume que existe logica de moderation.py que llamamos abajo)
    
    # Verificar si el mensaje es en biblioteca (hacer backup, sin moderación)
    if message.message_thread_id in [config.TOPIC_BIBLIOTECA_ESP, config.TOPIC_BIBLIOTECA_ING]:
        from modules.library import library_module
        await library_module.backup_message(message, context)
        return
    
    # Verificar si el mensaje es en peticiones (validar formato, sin moderación)
    if message.message_thread_id == config.TOPIC_PETICIONES:
        from modules.requests import request_module
        await request_module.check_manual_request(update, context)
        return
        
    # Verificar si el mensaje es en Ayuda
    if hasattr(config, 'TOPIC_AYUDA') and message.message_thread_id == config.TOPIC_AYUDA:
        text = (message.text or "").lower()
        if any(word in text for word in ['como subir', 'cómo subir', 'subir un libro', 'aportar']):
            await message.reply_text("📚 **Para subir un libro:**\nSolo envíalo al grupo en formato PDF o EPUB y nómbralo así:\n`Titulo - Autor.epub`\n\nYo me encargaré del resto. ✨", parse_mode='Markdown')
            return
        elif any(word in text for word in ['como pedir', 'cómo pedir', 'pedir un libro', 'peticion']):
            await message.reply_text("🙏 **Para pedir un libro:**\nVe al tema de **Peticiones** y escribe `/pedido`. Te guiaré paso a paso. ✨", parse_mode='Markdown')
            return
        elif any(word in text for word in ['buscar', 'encontrar', 'donde estan', 'dónde están']):
            await message.reply_text("🔍 **Para buscar un libro:**\nEscribe `/buscar título o autor` y te enviaré los resultados. También puedes ver los estrenos con `/lanzamientos`. ✨", parse_mode='Markdown')
            return
        else:
            await message.reply_text("🦋 He recibido tu duda. Si las guías no te ayudaron, por favor espera a que una de nuestras administradoras te asista. 💖")
            return
            
    # Pasar por sistema de moderación
    was_moderated = await moderation_module.check_message(update, context, user_data)
    
    if was_moderated:
        # Actualizar estado por riesgo
        await risk_module.update_user_status_by_risk(user_id)
        
        # Verificar umbral de riesgo
        await risk_module.check_risk_threshold(user_id, context)
        
        # Verificar combinaciones peligrosas
        await risk_module.check_dangerous_combinations(user_id, context)
        
        # Verificar pérdida de trusted
        await warnings_module.check_trusted_warnings_loss(user_id, context)
        return
        
    # Selene responde a menciones
    text = message.text or ""
    if "selene" in text.lower() and not text.startswith("/"):
        import random
        respuestas = [
            "✨ ¿Me llamabas?",
            "📖 Aquí estoy, lista para ayudarte con tus lecturas.",
            "🌙 Dime, ¿en qué te puedo ayudar hoy?",
            "📚 Siempre a tu servicio.",
            "✨ Selene a la escucha. ¿Buscas algún libro?",
            "🦋 Hola, ¿necesitas algo?"
        ]
        await message.reply_text(random.choice(respuestas))

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar nuevos miembros"""
    from modules.users import users_module
    await users_module.handle_new_member(update, context)

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar solicitud de ingreso al grupo"""
    from modules.users import users_module
    await users_module.handle_join_request(update, context)

async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar actualizaciones de miembros del chat (ej. unirse por link)"""
    result = update.chat_member
    if not result:
        return
        
    if result.new_chat_member.status == "member" and result.old_chat_member.status in ["left", "kicked"]:
        # Alguien nuevo entró. Veamos si usó un link
        if result.invite_link:
            link = result.invite_link.invite_link
            link_info = await db_manager.get_invite_link_info(link)
            
            if link_info:
                # Incrementar contador
                await db_manager.increment_invite_use(link)
                
                # Notificar al creador del link
                creator_id = link_info['creator_id']
                joined_user = result.new_chat_member.user
                
                msg = f"🎉 **¡Alguien se unió con tu link!**\n\n"
                msg += f"Usuario: @{joined_user.username or joined_user.first_name}\n"
                msg += "Recuerda que eres responsable de tus invitados."
                
                try:
                    await context.bot.send_message(chat_id=creator_id, text=msg, parse_mode='Markdown')
                except Exception as e:
                    print(f"No se pudo notificar al creador {creator_id}: {e}")
                    
                # Registrar el uso en audit_log
                await db_manager.add_audit_log(
                    admin_id=joined_user.id,
                    admin_username=joined_user.username,
                    action_type='join_by_invite',
                    target_user_id=creator_id,
                    target_username=None,
                    reason=f"Usó link: {link}"
                )
