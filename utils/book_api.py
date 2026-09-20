import httpx
import re
from urllib.parse import quote

async def get_book_metadata(filename: str, lang: str = None):
    """
    Busca metadatos de un libro usando la API de Google Books
    basándose en el nombre de archivo.
    """
    clean_name = re.sub(r'(?i)\.(pdf|epub|mobi)$', '', filename or '')
    clean_name = re.sub(r'^\d+[\.\-\s_]+', '', clean_name)
    clean_name = clean_name.replace('_', ' ').replace('-', ' ')
    clean_name = re.sub(r'(?i)\b(final|rev|ok|pdf|epub|mobi)\b', '', clean_name)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()

    if not clean_name:
        return None

    url = f"https://www.googleapis.com/books/v1/volumes?q={quote(clean_name)}&maxResults=1"
    if lang:
        url += f"&langRestrict={lang}"

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=8.0)

        if response.status_code != 200:
            return None

        data = response.json()
        if data.get('totalItems', 0) <= 0 or 'items' not in data:
            return None

        item = data['items'][0].get('volumeInfo') or {}
        title = item.get('title') or ''
        authors = item.get('authors') or []
        author = authors[0] if authors else ''
        description = item.get('description') or ''
        if len(description) > 500:
            description = description[:497] + "..."

        images = item.get('imageLinks') or {}
        cover_url = images.get('thumbnail') or images.get('smallThumbnail') or ''
        if cover_url:
            cover_url = cover_url.replace('http://', 'https://')
            cover_url = cover_url.replace('zoom=1', 'zoom=0')
            cover_url = cover_url.replace('&edge=curl', '')

        pages = item.get('pageCount') or 0
        year = (item.get('publishedDate') or '')[:4]

        categories = item.get('categories') or []
        category = categories[0] if categories else ''
        
        # Calcular tiempo de lectura estimado (250 palabras por página aprox, a 250 palabras por minuto = 1 min por página)
        reading_time_mins = pages
        reading_time_str = ""
        if reading_time_mins > 0:
            horas = reading_time_mins // 60
            mins = reading_time_mins % 60
            if horas > 0:
                reading_time_str = f"{horas}h {mins}m"
            else:
                reading_time_str = f"{mins}m"

        if not title:
            return None

        # Obtener rating de Goodreads
        gr_rating, gr_url = await get_goodreads_rating(title, author)
        
        # Fallback a Google Books
        if not gr_rating:
            gb_rating = item.get('averageRating')
            if gb_rating:
                gr_rating = str(gb_rating)
                gr_url = item.get('infoLink', '')
                rating_source = "Google Books"
            else:
                rating_source = None
        else:
            rating_source = "Goodreads"

        return {
            'title': title,
            'author': author,
            'description': description,
            'cover_url': cover_url,
            'pages': pages,
            'year': year,
            'category': category,
            'reading_time': reading_time_str,
            'gr_rating': gr_rating,
            'gr_url': gr_url,
            'rating_source': rating_source,
            'language': item.get('language') or 'es'
        }
    except Exception as e:
        print(f"Error consultando Google Books API para {clean_name}: {e}")
        return None

async def get_goodreads_rating(title: str, author: str):
    """
    Intenta obtener el rating desde la página de búsqueda de Goodreads.
    Devuelve (rating, url_del_libro).
    """
    if not title:
        return None, None
        
    query = quote(f"{title} {author}")
    url = f"https://www.goodreads.com/search?q={query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=8.0)
            
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Goodreads search results have class 'bookTitle' and 'minirating'
            rating_span = soup.find('span', class_='minirating')
            if rating_span:
                # El texto suele ser: " 4.15 avg rating — 1,234 ratings"
                text = rating_span.get_text(strip=True)
                match = re.search(r'([\d\.]+)\s+avg rating', text)
                rating = match.group(1) if match else None
                
                # Obtener enlace al libro
                book_link = soup.find('a', class_='bookTitle')
                book_url = ""
                if book_link and 'href' in book_link.attrs:
                    book_url = "https://www.goodreads.com" + book_link['href']
                    
                return rating, book_url
    except Exception as e:
        print(f"Error extrayendo Goodreads rating para {title}: {e}")
        
    return None, None


async def download_cover_bytes(cover_url: str):
    """Descargar bytes de portada. Devuelve None si falla."""
    if not cover_url:
        return None
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(cover_url, timeout=8.0)
        if response.status_code == 200 and response.content:
            return response.content
    except Exception as e:
        print(f"Error descargando portada: {e}")
    return None
