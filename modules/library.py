"""
Módulo de Biblioteca
Reorganiza archivos en biblioteca principal y hace backup automático
Incluye validación anti-fake, auto-renombrado y metadatos de Google Books
"""

import os
import re
import asyncio
import tempfile
from telegram import Message, InputMediaDocument, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import config
from database.db_manager import db_manager
from utils.book_api import get_book_metadata, download_cover_bytes

# Buffer global: acumula TODOS los mensajes por tema antes de procesar
_batch_buffer = {}
_batch_tasks = {}

PDF_MAGIC = b'%PDF'
ZIP_MAGIC = (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')


class LibraryModule:

    async def backup_message(self, message: Message, context: ContextTypes.DEFAULT_TYPE):
        """Recibir mensaje de biblioteca"""
        if message.from_user and message.from_user.id == context.bot.id:
            return

        is_any_admin = message.from_user and message.from_user.id in config.ADMIN_IDS
        is_main_admin = message.from_user and message.from_user.id == config.ADMIN_ID

        topic_name = None
        backup_topic_id = None

        if message.message_thread_id == config.TOPIC_BIBLIOTECA_ESP:
            topic_name = 'biblioteca_español'
            backup_topic_id = config.BACKUP_BIBLIOTECA_ESP_TOPIC
        elif message.message_thread_id == config.TOPIC_BIBLIOTECA_ING:
            topic_name = 'biblioteca_inglés'
            backup_topic_id = config.BACKUP_BIBLIOTECA_ING_TOPIC
        else:
            return

        if not is_any_admin or not is_main_admin:
            await self._simple_backup(message, context, topic_name, backup_topic_id)
            return

        key = f"{message.chat_id}_{message.message_thread_id}"

        if key not in _batch_buffer:
            _batch_buffer[key] = {
                'messages': [],
                'topic_name': topic_name,
                'backup_topic_id': backup_topic_id,
                'context': context,
                'chat_id': message.chat_id,
                'thread_id': message.message_thread_id
            }

        _batch_buffer[key]['messages'].append(message)

        if key in _batch_tasks:
            _batch_tasks[key].cancel()

        async def process_batch():
            await asyncio.sleep(15)
            data = _batch_buffer.pop(key, None)
            _batch_tasks.pop(key, None)
            if data:
                await self._process_batch(data)

        _batch_tasks[key] = asyncio.create_task(process_batch())

    @staticmethod
    def _extract_sort_number(filename: str) -> int:
        if not filename:
            return 999
        match = re.match(r'^(\d+)', filename.strip())
        return int(match.group(1)) if match else 999

    @staticmethod
    def _ebook_ext(filename: str):
        name = (filename or '').lower()
        if name.endswith('.pdf'):
            return 'pdf'
        if name.endswith('.epub'):
            return 'epub'
        return None

    @staticmethod
    def _lang_hint(topic_name: str):
        if topic_name and 'inglé' in topic_name:
            return 'en'
        if topic_name and 'español' in topic_name:
            return 'es'
        return None

    @staticmethod
    def _safe_filename(title: str, author: str, ext: str) -> str:
        base = f"{title} - {author}" if author else title
        base = re.sub(r'[<>:"/\\|?*\n\r]', '', base)
        base = re.sub(r'\s+', ' ', base).strip(' .')
        if not base:
            base = 'libro'
        filename = f"{base}.{ext}"
        if len(filename) > 180:
            filename = f"{base[:170]}.{ext}"
        return filename

    @staticmethod
    def _validate_magic(path: str, ext: str) -> bool:
        try:
            with open(path, 'rb') as f:
                header = f.read(256)
        except Exception:
            return False
        if ext == 'pdf':
            return header.startswith(PDF_MAGIC)
        if ext == 'epub':
            return header.startswith(ZIP_MAGIC)
        return False

    @staticmethod
    def _build_premium_caption(metadata: dict, fallback: str = None) -> str:
        if not metadata:
            return (fallback or '')[:1024]
        lines = [f"📖 **{metadata.get('title') or 'Libro'}**"]
        if metadata.get('author'):
            lines.append(f"✍️ {metadata['author']}")
        extra = []
        if metadata.get('year'):
            extra.append(str(metadata['year']))
        if metadata.get('pages'):
            extra.append(f"{metadata['pages']} págs.")
        if extra:
            lines.append("📌 " + " | ".join(extra))
        if metadata.get('gr_rating'):
            rating_url = metadata.get('gr_url', 'https://www.goodreads.com/')
            source = metadata.get('rating_source', 'Goodreads')
            lines.append(f"⭐ Calificación ({source}): [{metadata['gr_rating']}/5]({rating_url})")
        if metadata.get('reading_time'):
            lines.append(f"⏳ Tiempo est. de lectura: {metadata['reading_time']}")
        if metadata.get('category'):
            cat = metadata['category'].split(' / ')[0].replace(' ', '').replace('-', '')
            lines.append(f"#{cat}")
        if metadata.get('description'):
            desc = metadata['description'].replace('\n', ' ')
            if len(desc) > 300:
                desc = desc[:297] + "..."
            lines.append(f"\n📝 *Sinopsis:*\n{desc}")
        caption = '\n'.join(lines).strip()
        if fallback and fallback not in caption:
            caption = f"{caption}\n\n{fallback}" if caption else fallback
        return caption[:1024]

    async def _process_ebook(self, message: Message, context, topic_name: str):
        """Descargar, validar y enriquecer un PDF/EPUB. Limpia temp si hay error."""
        result = {
            'fake': False,
            'skip': True,
            'temp_path': None,
            'filename': message.document.file_name if message.document else None,
            'metadata': None,
            'caption': message.caption,
            'cover_bytes': None,
            'file_id': message.document.file_id if message.document else None,
        }
        if not message.document:
            return result

        ext = self._ebook_ext(message.document.file_name)
        if not ext:
            return result

        file_size = message.document.file_size or 0
        if file_size > config.TELEGRAM_BOT_DOWNLOAD_LIMIT:
            result['skip'] = True
            return result

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}')
        tmp.close()
        path = tmp.name
        try:
            tg_file = await context.bot.get_file(message.document.file_id)
            await tg_file.download_to_drive(path)

            if not self._validate_magic(path, ext):
                result['fake'] = True
                result['skip'] = False
                try:
                    os.unlink(path)
                except Exception:
                    pass
                result['temp_path'] = None
                return result

            # Limpiar Metadatos (Anti-piratería)
            if ext == 'pdf':
                try:
                    from pypdf import PdfReader, PdfWriter
                    reader = PdfReader(path)
                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)
                    # Añadir metadatos vacíos para limpiar
                    writer.add_metadata({})
                    tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                    tmp_out.close()
                    with open(tmp_out.name, "wb") as f_out:
                        writer.write(f_out)
                    os.replace(tmp_out.name, path)
                except Exception as e:
                    print(f"Error limpiando metadatos PDF: {e}")

            metadata = await get_book_metadata(
                message.document.file_name,
                lang=self._lang_hint(topic_name)
            )
            
            # Nombre real para la Base de Datos
            filename = message.document.file_name
            caption = message.caption
            cover_bytes = None
            if metadata:
                filename = self._safe_filename(
                    metadata.get('title') or 'Libro',
                    metadata.get('author') or '',
                    ext
                )
                caption = self._build_premium_caption(metadata, message.caption)
                cover_bytes = await download_cover_bytes(metadata.get('cover_url'))
                
            # Nombre neutro para subir a Telegram
            import uuid
            upload_filename = f"AGY-{str(uuid.uuid4())[:8].upper()}.{ext}"
            new_path = os.path.join(os.path.dirname(path), upload_filename)
            try:
                os.replace(path, new_path)
                path = new_path
            except Exception:
                pass

            result.update({
                'fake': False,
                'skip': False,
                'temp_path': path,
                'filename': filename,          # Para BD
                'upload_filename': upload_filename, # Para archivo físico
                'metadata': metadata,
                'caption': caption,
                'cover_bytes': cover_bytes,
            })
            return result
        except Exception as e:
            print(f"Error procesando ebook: {e}")
            try:
                os.unlink(path)
            except Exception:
                pass
            result['temp_path'] = None
            result['skip'] = True
            return result

    async def _cleanup_processed(self, processed_list: list):
        for item in processed_list or []:
            path = item.get('temp_path') if isinstance(item, dict) else None
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass

    async def _reject_fake_file(self, message: Message, context):
        """Borrar archivo falso y avisar."""
        filename = message.document.file_name if message.document else 'archivo'
        user = message.from_user
        mention = f"@{user.username}" if user and user.username else (user.first_name if user else 'alguien')
        try:
            await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
        except Exception as e:
            print(f"Error borrando archivo falso: {e}")

        warn = (
            f"🚫 Archivo rechazado (anti-fake)\n\n"
            f"El archivo `{filename}` no es un PDF/EPUB real "
            f"(el contenido no coincide con la extensión).\n"
            f"Subido por: {mention}"
        )
        try:
            await context.bot.send_message(
                chat_id=config.GROUP_ID,
                message_thread_id=config.TOPIC_ADMINISTRACION,
                text=warn,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error avisando archivo falso: {e}")
        if user:
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=(
                        "Tu archivo fue rechazado porque no es un PDF o EPUB válido "
                        "(por ejemplo, un .txt renombrado a .pdf)."
                    )
                )
            except Exception:
                pass

    def _classify_messages(self, messages: list):
        photos = []
        pdfs = []
        epubs = []
        separators = []

        for msg in messages:
            if msg.photo:
                photos.append(msg)
            elif msg.document:
                fname = (msg.document.file_name or '').lower()
                if fname.endswith('.pdf'):
                    pdfs.append(msg)
                elif fname.endswith('.epub'):
                    epubs.append(msg)
                else:
                    pdfs.append(msg)
            elif msg.video:
                photos.append(msg)
            elif msg.sticker or msg.text:
                separators.append(msg)

        pdfs.sort(key=lambda m: self._extract_sort_number(m.document.file_name if m.document else ''))
        epubs.sort(key=lambda m: self._extract_sort_number(m.document.file_name if m.document else ''))
        return photos, pdfs, epubs, separators

    async def _process_batch(self, data: dict):
        """Procesar batch: borrar originales → re-enviar organizado → backup"""
        messages = sorted(data['messages'], key=lambda m: m.message_id)
        context = data['context']
        chat_id = data['chat_id']
        thread_id = data['thread_id']
        topic_name = data['topic_name']
        backup_topic_id = data['backup_topic_id']

        photos, pdfs, epubs, separators = self._classify_messages(messages)

        all_captions = []
        for msg in messages:
            if msg.caption and msg.caption not in all_captions:
                all_captions.append(msg.caption)
        first_caption = all_captions[0] if all_captions else None

        processed_pdfs = []
        processed_epubs = []
        keep_messages = list(photos) + list(separators)

        for msg in pdfs:
            if self._ebook_ext(msg.document.file_name if msg.document else '') == 'pdf':
                proc = await self._process_ebook(msg, context, topic_name)
                if proc['fake']:
                    await self._reject_fake_file(msg, context)
                    continue
                processed_pdfs.append((msg, proc))
                keep_messages.append(msg)
            else:
                processed_pdfs.append((msg, None))
                keep_messages.append(msg)

        for msg in epubs:
            proc = await self._process_ebook(msg, context, topic_name)
            if proc['fake']:
                await self._reject_fake_file(msg, context)
                continue
            processed_epubs.append((msg, proc))
            keep_messages.append(msg)

        for msg in keep_messages:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            except Exception as e:
                print(f"Error borrando mensaje {msg.message_id}: {e}")

        try:
            if photos:
                await self._send_organized_group(
                    photos, context, chat_id, thread_id, first_caption, None
                )

            if processed_pdfs:
                cap = first_caption if not photos else None
                await self._send_organized_processed(
                    processed_pdfs, context, chat_id, thread_id, cap
                )

            if processed_epubs:
                cap = first_caption if not photos and not processed_pdfs else None
                await self._send_organized_processed(
                    processed_epubs, context, chat_id, thread_id, cap
                )

            for msg in separators:
                await self._resend_single(msg, context, chat_id, thread_id)

            if photos:
                await self._backup_media_group(
                    photos, context, topic_name, backup_topic_id, first_caption
                )

            if processed_pdfs:
                cap = first_caption if not photos else None
                await self._backup_processed(
                    processed_pdfs, context, topic_name, backup_topic_id, cap
                )

            if processed_epubs:
                cap = first_caption if not photos and not processed_pdfs else None
                await self._backup_processed(
                    processed_epubs, context, topic_name, backup_topic_id, cap
                )

            for msg in separators:
                await self._backup_single(msg, context, topic_name, backup_topic_id)
        finally:
            await self._cleanup_processed([p for _, p in processed_pdfs if p])
            await self._cleanup_processed([p for _, p in processed_epubs if p])

    async def _simple_backup(self, message: Message, context, topic_name: str, backup_topic_id: int):
        """Backup simple sin reorganización para mensajes de otros usuarios"""
        try:
            if message.document and self._ebook_ext(message.document.file_name):
                proc = await self._process_ebook(message, context, topic_name)
                try:
                    if proc['fake']:
                        await self._reject_fake_file(message, context)
                        return

                    target_thread_id = message.message_thread_id
                    new_topic_name = topic_name
                    new_backup_topic_id = backup_topic_id
                    
                    # Detección de duplicados en tiempo real
                    search_results = await db_manager.search_library(proc['filename'])
                    import difflib
                    is_duplicate = False
                    for r in search_results:
                        if difflib.SequenceMatcher(None, proc['filename'].lower(), r['file_name'].lower()).ratio() > 0.85:
                            is_duplicate = True
                            break
                    if is_duplicate:
                        try:
                            await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
                        except:
                            pass
                        try:
                            await context.bot.send_message(
                                chat_id=message.from_user.id,
                                text=f"⚠️ Hola @{message.from_user.username or message.from_user.first_name}, el libro **{proc['filename']}** que intentaste subir ya existe en nuestra biblioteca. ¡Gracias de todos modos por tu intención de aportar!",
                                parse_mode='Markdown'
                            )
                        except:
                            pass
                        return
                    
                    # Detección automática de idioma
                    lang = 'es'
                    if proc.get('metadata') and proc['metadata'].get('language'):
                        lang = proc['metadata']['language']
                    elif proc.get('filename') and any(word in proc['filename'].lower() for word in ['the', 'of', 'and', 'in', 'to', 'a']):
                        lang = 'en'
                        
                    if lang == 'en':
                        target_thread_id = config.TOPIC_BIBLIOTECA_ING
                        new_topic_name = 'biblioteca_inglés'
                        new_backup_topic_id = config.BACKUP_BIBLIOTECA_ING_TOPIC
                    else:
                        target_thread_id = config.TOPIC_BIBLIOTECA_ESP
                        new_topic_name = 'biblioteca_español'
                        new_backup_topic_id = config.BACKUP_BIBLIOTECA_ESP_TOPIC

                    sent_main = None
                    if not proc['skip'] and proc.get('temp_path'):
                        try:
                            with open(proc['temp_path'], 'rb') as f:
                                sent_main = await context.bot.send_document(
                                    chat_id=message.chat_id,
                                    document=f,
                                    filename=proc.get('upload_filename', proc['filename']),
                                    caption=proc.get('caption') or message.caption,
                                    message_thread_id=target_thread_id,
                                    read_timeout=60,
                                    write_timeout=60
                                )
                            try:
                                await context.bot.delete_message(
                                    chat_id=message.chat_id,
                                    message_id=message.message_id
                                )
                                # Avisar si se movió de tema
                                if target_thread_id != message.message_thread_id:
                                    topic_str = "Biblioteca Inglés" if lang == 'en' else "Biblioteca Español"
                                    await context.bot.send_message(
                                        chat_id=message.chat_id,
                                        message_thread_id=message.message_thread_id,
                                        text=f"✈️ @{message.from_user.username or message.from_user.first_name}, tu libro ha sido movido automáticamente a {topic_str} por detección de idioma."
                                    )
                                    
                                # Reconocimiento automático
                                author = proc.get('metadata', {}).get('author', 'Desconocido')
                                pages = proc.get('metadata', {}).get('pages', 'N/A')
                                title = proc.get('metadata', {}).get('title', proc['filename'])
                                await context.bot.send_message(
                                    chat_id=message.chat_id,
                                    message_thread_id=target_thread_id,
                                    text=f"📚 **NUEVO APORTE** 📚\n\n📖 **Título:** {title}\n👤 **Autor:** {author}\n📄 **Páginas:** {pages}\n\n✨ _Subido por: @{message.from_user.username or message.from_user.first_name}_\n¡Muchas gracias por contribuir a nuestra biblioteca! 💖",
                                    parse_mode='Markdown'
                                )
                            except Exception:
                                pass
                        except Exception as e:
                            print(f"Error reenviando ebook renombrado: {e}")
                            sent_main = None

                    await self._backup_processed(
                        [(sent_main or message, proc)],
                        context, new_topic_name, new_backup_topic_id,
                        proc.get('caption') or message.caption
                    )

                    if message.from_user:
                        new_rank = await db_manager.increment_user_contributions(message.from_user.id)
                        if new_rank:
                            await self._notify_rank_up(message.from_user, new_rank, context)
                    await self._check_pending_requests(sent_main or message, context)
                finally:
                    await self._cleanup_processed([proc])
                return

            if message.document or message.photo or message.video:
                await self._backup_media_group(
                    [message], context, topic_name, backup_topic_id, message.caption
                )
                if message.from_user:
                    new_rank = await db_manager.increment_user_contributions(message.from_user.id)
                    if new_rank:
                        await self._notify_rank_up(message.from_user, new_rank, context)
                if message.document and message.document.file_name:
                    await self._check_pending_requests(message, context)
            elif message.sticker or message.text:
                await self._backup_single(message, context, topic_name, backup_topic_id)
        except Exception as e:
            print(f"Error backup simple: {e}")

    async def _notify_rank_up(self, user, rank_id: int, context):
        """Notificar a un usuario que ha subido de rango"""
        ranks = {
            1: ("Colaborador", "¡Gracias por empezar a compartir con la comunidad!"),
            2: ("Aportador", "¡Tus aportes son muy valiosos para todos!"),
            3: ("Aportador Estrella", "¡Wow! Eres uno de nuestros mejores aportadores."),
            4: ("Guardián", "¡Increíble! Eres una leyenda de la biblioteca.")
        }
        if rank_id not in ranks:
            return
            
        rank_name, msg = ranks[rank_id]
        text = f"🎉 ¡Felicidades @{user.username or user.first_name}!\n\nHas subido de rango a **{rank_name}**. {msg}"
        
        try:
            await context.bot.send_message(
                chat_id=config.GROUP_ID,
                text=text,
                parse_mode='Markdown'
            )
        except Exception:
            pass

    async def _check_pending_requests(self, message: Message, context):
        """Buscar pedidos pendientes que coincidan con el archivo subido y notificar"""
        try:
            if not message.document or not message.document.file_name:
                return
            filename = message.document.file_name
            clean_name = re.sub(r'\.\w+$', '', filename)
            clean_name = re.sub(r'^\d+[\.\-\s]*', '', clean_name)
            clean_name = clean_name.strip()

            if len(clean_name) < 3:
                return

            matching = await db_manager.get_pending_requests_matching(clean_name)
            if not matching:
                return

            for request in matching:
                try:
                    await db_manager.update_request_status(request['id'], 'atendido')
                except Exception:
                    pass

                user_id = request['user_id']
                try:
                    link = f"https://t.me/c/{str(message.chat_id)[4:]}/{message.message_id}"
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🎉 **¡Tu pedido fue atendido!**\n\n"
                            f"📖 *{request['title']}*\n"
                            f"✍️ {request.get('author', '')}\n\n"
                            f"El libro acaba de ser subido a la biblioteca.\n"
                            f"[Ver en la biblioteca]({link})"
                        ),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f"Error notificando pedido atendido a {user_id}: {e}")

            if matching and message.from_user:
                try:
                    uploader = message.from_user.username or message.from_user.first_name
                    titles = ", ".join([f"*{r['title']}*" for r in matching])
                    await context.bot.send_message(
                        chat_id=config.GROUP_ID,
                        text=f"🎉 ¡Gracias a @{uploader} por subir {titles}! \nEste libro estaba en la lista de peticiones.",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f"Error enviando agradecimiento público: {e}")
        except Exception as e:
            print(f"Error check_pending_requests: {e}")

    async def _send_organized_group(self, messages: list, context, chat_id: int, thread_id: int, caption: str = None, processed=None):
        """Enviar media group organizado al grupo principal (fotos/videos o file_id)."""
        try:
            media_list = []
            for i, msg in enumerate(messages):
                cap = caption if i == 0 and caption else (msg.caption if i == 0 else None)
                if msg.document:
                    media_list.append(InputMediaDocument(media=msg.document.file_id, caption=cap))
                elif msg.photo:
                    media_list.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=cap))
                elif msg.video:
                    media_list.append(InputMediaVideo(media=msg.video.file_id, caption=cap))

            if media_list:
                return await context.bot.send_media_group(
                    chat_id=chat_id,
                    media=media_list,
                    message_thread_id=thread_id,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=30
                )
        except Exception as e:
            print(f"Error re-enviando grupo organizado: {e}")
        return []

    async def _send_organized_processed(self, pairs: list, context, chat_id: int, thread_id: int, caption: str = None):
        """Reenviar PDFs/EPUBs ya procesados (renombrados si aplica)."""
        handles = []
        try:
            media_list = []
            for i, (msg, proc) in enumerate(pairs):
                cap = None
                if i == 0:
                    cap = (proc.get('caption') if proc else None) or caption or msg.caption
                if proc and not proc.get('skip') and proc.get('temp_path'):
                    fh = open(proc['temp_path'], 'rb')
                    handles.append(fh)
                    media_list.append(InputMediaDocument(
                        media=fh,
                        filename=proc.get('filename'),
                        caption=cap
                    ))
                elif msg.document:
                    media_list.append(InputMediaDocument(media=msg.document.file_id, caption=cap))
            if media_list:
                return await context.bot.send_media_group(
                    chat_id=chat_id,
                    media=media_list,
                    message_thread_id=thread_id,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=30
                )
        except Exception as e:
            print(f"Error re-enviando ebooks procesados: {e}")
        finally:
            for fh in handles:
                try:
                    fh.close()
                except Exception:
                    pass
        return []

    async def _resend_single(self, message: Message, context, chat_id: int, thread_id: int):
        """Re-enviar mensaje individual (sticker/texto) al grupo principal"""
        try:
            if message.sticker:
                await context.bot.send_sticker(
                    chat_id=chat_id,
                    sticker=message.sticker.file_id,
                    message_thread_id=thread_id
                )
            elif message.text:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message.text,
                    message_thread_id=thread_id
                )
        except Exception as e:
            print(f"Error re-enviando individual: {e}")

    async def _backup_media_group(self, messages: list, context, topic_name: str, backup_topic_id: int, caption: str = None):
        """Enviar media group al backup (fotos/videos/file_id)."""
        try:
            media_list = []
            for i, msg in enumerate(messages):
                cap = caption if i == 0 and caption else (msg.caption if i == 0 else None)
                if msg.document:
                    media_list.append(InputMediaDocument(media=msg.document.file_id, caption=cap))
                elif msg.photo:
                    media_list.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=cap))
                elif msg.video:
                    media_list.append(InputMediaVideo(media=msg.video.file_id, caption=cap))

            if media_list:
                sent = await context.bot.send_media_group(
                    chat_id=config.BACKUP_GROUP_ID,
                    media=media_list,
                    message_thread_id=backup_topic_id,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=30
                )
                for i, msg in enumerate(messages):
                    backup_id = sent[i].message_id if i < len(sent) else None
                    await self._save_to_db(msg, topic_name, backup_id)
        except Exception as e:
            print(f"Error backup media group: {e}")

    async def _backup_processed(self, pairs: list, context, topic_name: str, backup_topic_id: int, caption: str = None):
        """Backup de ebooks con caption premium y portada si existe."""
        for i, (msg, proc) in enumerate(pairs):
            cap = None
            if proc:
                cap = proc.get('caption')
            if i == 0 and not cap:
                cap = caption or (msg.caption if msg else None)
            backup_msg_id = None
            try:
                if proc and proc.get('cover_bytes'):
                    try:
                        await context.bot.send_photo(
                            chat_id=config.BACKUP_GROUP_ID,
                            photo=proc['cover_bytes'],
                            caption=cap,
                            message_thread_id=backup_topic_id
                        )
                        cap = None
                    except Exception as e:
                        print(f"Error enviando portada al backup: {e}")

                if proc and not proc.get('skip') and proc.get('temp_path'):
                    # Construir botón de Acción Rápida si tenemos el autor
                    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                    reply_markup = None
                    if proc.get('metadata') and proc['metadata'].get('author'):
                        # Solo primeros 50 chars por limites de telegram callback_data
                        author_name = proc['metadata']['author'][:50]
                        reply_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔍 Buscar más de este autor", callback_data=f"dir_author|{author_name}")]
                        ])
                        
                    with open(proc['temp_path'], 'rb') as f:
                        sent = await context.bot.send_document(
                            chat_id=config.BACKUP_GROUP_ID,
                            document=f,
                            filename=proc.get('upload_filename', proc.get('filename')),
                            caption=cap,
                            message_thread_id=backup_topic_id,
                            reply_markup=reply_markup,
                            read_timeout=120,
                            write_timeout=120
                        )
                    backup_msg_id = sent.message_id
                    sent_file_id = sent.document.file_id if sent and sent.document else None
                    await self._save_to_db(
                        msg, topic_name, backup_msg_id,
                        file_name=proc.get('filename'),
                        caption=proc.get('caption') or cap,
                        original_year=int(proc['metadata']['year']) if proc.get('metadata') and proc['metadata'].get('year') else None,
                        genre=proc['metadata'].get('category', 'Desconocido') if proc.get('metadata') else 'Desconocido',
                        page_count=int(proc['metadata']['pages']) if proc.get('metadata') and proc['metadata'].get('pages') else None,
                        override_file_id=sent_file_id
                    )
                elif msg and msg.document:
                    sent = await context.bot.send_document(
                        chat_id=config.BACKUP_GROUP_ID,
                        document=msg.document.file_id,
                        caption=cap,
                        message_thread_id=backup_topic_id
                    )
                    backup_msg_id = sent.message_id
                    await self._save_to_db(msg, topic_name, backup_msg_id)
            except Exception as e:
                print(f"Error backup ebook procesado: {e}")
                if msg:
                    await self._save_to_db(msg, topic_name, backup_msg_id)

    async def _backup_single(self, message: Message, context, topic_name: str, backup_topic_id: int):
        """Enviar mensaje individual al backup"""
        backup_msg_id = None
        try:
            if message.sticker:
                sent = await context.bot.send_sticker(
                    chat_id=config.BACKUP_GROUP_ID,
                    sticker=message.sticker.file_id,
                    message_thread_id=backup_topic_id
                )
                backup_msg_id = sent.message_id
            elif message.text:
                sent = await context.bot.send_message(
                    chat_id=config.BACKUP_GROUP_ID,
                    message_thread_id=backup_topic_id,
                    text=message.text
                )
                backup_msg_id = sent.message_id
        except Exception as e:
            print(f"Error backup individual: {e}")

        await self._save_to_db(message, topic_name, backup_msg_id)

    async def _save_to_db(self, message: Message, topic_name: str, backup_msg_id, file_name=None, caption=None, original_year=None, genre=None, page_count=None, override_file_id=None):
        """Guardar registro en base de datos"""
        if not message:
            return
        user_id = message.from_user.id if message.from_user else None
        content_type = file_id = None
        file_size = None
        saved_name = file_name
        saved_caption = caption if caption is not None else message.caption

        if message.document:
            content_type = 'document'
            saved_name = saved_name or message.document.file_name
            file_id, file_size = override_file_id or message.document.file_id, message.document.file_size
        elif message.photo:
            content_type = 'photo'
            file_id, file_size = message.photo[-1].file_id, message.photo[-1].file_size
        elif message.video:
            content_type = 'video'
            file_id, file_size = message.video.file_id, message.video.file_size
        elif message.sticker:
            content_type = 'sticker'
            file_id, file_size = message.sticker.file_id, message.sticker.file_size
        elif message.text:
            content_type = 'text'

        await db_manager.save_library_backup(
            topic_name=topic_name,
            message_id=message.message_id,
            user_id=user_id,
            content_type=content_type,
            file_name=saved_name,
            file_id=file_id,
            file_size=file_size,
            caption=saved_caption,
            text_content=message.text,
            backup_channel_msg_id=backup_msg_id,
            original_year=original_year,
            genre=genre,
            page_count=page_count
        )


library_module = LibraryModule()
