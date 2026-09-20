from telegram import Update, InlineQueryResultCachedDocument, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
import uuid

# Importar db_manager (asegúrate de que tenga método para buscar con file_id)
from database.db_manager import db_manager

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar búsquedas inline (@bot libro)"""
    query = update.inline_query.query
    if not query or len(query) < 2:
        return
        
    # Necesitamos file_id para mandar el documento directamente. 
    # search_library no devuelve file_id. Usaremos una query propia acá rápida o agregamos a db_manager
    import aiosqlite
    import config
    
    inline_results = []
    
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        like_query = f"%{query}%"
        # Traer file_id y caption
        async with db.execute("""
            SELECT id, file_name, file_id, caption
            FROM library_backup
            WHERE (file_name LIKE ? OR caption LIKE ?) AND file_id IS NOT NULL AND file_name IS NOT NULL
            ORDER BY timestamp DESC LIMIT 20
        """, (like_query, like_query)) as cursor:
            rows = await cursor.fetchall()
            
            for r in rows:
                if not r['file_id']: continue
                
                # Crear resultado cacheado
                result = InlineQueryResultCachedDocument(
                    id=str(r['id']),
                    title=r['file_name'],
                    document_file_id=r['file_id'],
                    description="📖 Toca para enviar este libro",
                    caption=r['caption']
                )
                inline_results.append(result)
                
    if not inline_results:
        # Si no hay resultados, mostramos un mensaje
        inline_results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="❌ No se encontraron libros",
                description="Intenta con otro título o autor",
                input_message_content=InputTextMessageContent("No encontré ese libro en la biblioteca 😥")
            )
        )
                
    await update.inline_query.answer(inline_results, cache_time=10)

async def chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar cuando un usuario selecciona un resultado inline para sumarlo al contador"""
    result = update.chosen_inline_result
    if not result:
        return
        
    try:
        # El id que mandamos es el id de library_backup
        book_id = int(result.result_id)
        await db_manager.increment_download(book_id)
    except ValueError:
        pass # Si no es un id valido (por ej el articulo vacio)
