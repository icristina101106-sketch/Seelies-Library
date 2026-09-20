"""
Utilidades para análisis de texto
Detección de links, spam, palabras prohibidas, etc.
"""

import re
from fuzzywuzzy import fuzz
from typing import List, Tuple, Optional

class TextAnalyzer:
    
    # Patrones de links
    LINK_PATTERNS = [
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        r't\.me/[a-zA-Z0-9_]+',
        r'telegram\.me/[a-zA-Z0-9_]+',
        r'bit\.ly/[a-zA-Z0-9]+',
        r'tinyurl\.com/[a-zA-Z0-9]+',
        r'goo\.gl/[a-zA-Z0-9]+',
    ]
    
    # Patrones de invitaciones
    INVITE_PATTERNS = [
        r't\.me/joinchat/[a-zA-Z0-9_-]+',
        r't\.me/\+[a-zA-Z0-9_-]+',
        r'telegram\.me/joinchat/[a-zA-Z0-9_-]+',
    ]
    
    @staticmethod
    def detect_links(text: str) -> List[str]:
        """Detectar todos los links en un texto"""
        if not text:
            return []
        
        links = []
        for pattern in TextAnalyzer.LINK_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            links.extend(matches)
        
        return links
    
    @staticmethod
    def has_links(text: str) -> bool:
        """Verificar si el texto contiene links"""
        return len(TextAnalyzer.detect_links(text)) > 0
    
    @staticmethod
    def detect_invites(text: str) -> List[str]:
        """Detectar invitaciones a grupos"""
        if not text:
            return []
        
        invites = []
        for pattern in TextAnalyzer.INVITE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            invites.extend(matches)
        
        return invites
    
    @staticmethod
    def has_invites(text: str) -> bool:
        """Verificar si el texto contiene invitaciones"""
        return len(TextAnalyzer.detect_invites(text)) > 0
    
    @staticmethod
    def check_forbidden_words(text: str, forbidden_words: List[dict]) -> Optional[Tuple[str, str, str]]:
        """
        Verificar si el texto contiene palabras prohibidas
        Retorna: (palabra, severidad, acción) o None
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Ordenar por severidad (graves primero)
        severity_order = {'grave': 0, 'media': 1, 'leve': 2}
        sorted_words = sorted(forbidden_words, key=lambda x: severity_order.get(x['severity'], 3))
        
        for word_data in sorted_words:
            word = word_data['word'].lower()
            
            if word_data.get('is_regex', False):
                # Búsqueda por regex
                if re.search(word, text_lower):
                    return (word_data['word'], word_data['severity'], word_data['action'])
            else:
                # Búsqueda exacta de palabra
                if word in text_lower:
                    return (word_data['word'], word_data['severity'], word_data['action'])
        
        return None
    
    @staticmethod
    def normalize_filename(filename: str) -> str:
        """Normalizar nombre de archivo para comparación"""
        if not filename:
            return ""
        
        # Convertir a minúsculas
        normalized = filename.lower()
        
        # Remover extensión
        normalized = re.sub(r'\.[a-z0-9]+$', '', normalized)
        
        # Remover caracteres especiales
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
        
        # Remover espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remover espacios al inicio y final
        normalized = normalized.strip()
        
        return normalized
    
    @staticmethod
    def compare_filenames(filename1: str, filename2: str) -> Tuple[float, str]:
        """
        Comparar dos nombres de archivo
        Retorna: (similitud 0-1, tipo: 'exacto' o 'probable')
        """
        if not filename1 or not filename2:
            return (0.0, 'ninguno')
        
        # Normalizar ambos nombres
        norm1 = TextAnalyzer.normalize_filename(filename1)
        norm2 = TextAnalyzer.normalize_filename(filename2)
        
        # Comparación exacta
        if norm1 == norm2:
            return (1.0, 'exacto')
        
        # Comparación fuzzy
        similarity = fuzz.ratio(norm1, norm2) / 100.0
        
        if similarity >= 0.85:
            return (similarity, 'probable')
        
        return (similarity, 'diferente')
    
    @staticmethod
    def detect_aggressive_tone(text: str) -> bool:
        """
        Detectar tono agresivo básico
        Esto es una detección simple, no perfecta
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Patrones de agresividad
        aggressive_patterns = [
            r'cállate',
            r'callate',
            r'cierra la boca',
            r'vete al',
            r'lárgate',
            r'largate',
            r'no me importa',
            r'me vale',
            r'qué te importa',
            r'que te importa',
        ]
        
        for pattern in aggressive_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Detectar MAYÚSCULAS SOSTENIDAS (gritos)
        words = text.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 3]
        if len(caps_words) >= 3:
            return True
        
        # Detectar signos de exclamación múltiples
        if text.count('!') >= 3:
            return True
        
        return False
    
    @staticmethod
    def is_suspicious_name(name: str) -> bool:
        """Detectar nombres sospechosos"""
        if not name:
            return True
        
        # Muy corto
        if len(name) < 2:
            return True
        
        # Solo números
        if name.isdigit():
            return True
        
        # Solo caracteres especiales
        if re.match(r'^[^a-zA-Z0-9]+$', name):
            return True
        
        # Muchos números consecutivos
        if re.search(r'\d{5,}', name):
            return True
        
        return False
    
    @staticmethod
    def extract_request_data(text: str) -> dict:
        """
        Intentar extraer datos de un pedido de libro del texto
        Retorna dict con: titulo, autor, idioma, formato
        """
        data = {
            'titulo': None,
            'autor': None,
            'idioma': None,
            'formato': None
        }
        
        if not text:
            return data
        
        lines = text.strip().split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            if 'título' in line_lower or 'titulo' in line_lower:
                data['titulo'] = line.split(':', 1)[-1].strip()
            elif 'autor' in line_lower:
                data['autor'] = line.split(':', 1)[-1].strip()
            elif 'idioma' in line_lower:
                data['idioma'] = line.split(':', 1)[-1].strip()
            elif 'formato' in line_lower:
                data['formato'] = line.split(':', 1)[-1].strip()
        
        return data
    
    @staticmethod
    def validate_request_format(data: dict) -> Tuple[bool, List[str]]:
        """
        Validar que un pedido tenga todos los campos requeridos
        Retorna: (es_valido, campos_faltantes)
        """
        required_fields = ['titulo', 'autor', 'idioma', 'formato']
        missing = []
        
        for field in required_fields:
            if not data.get(field) or data[field].strip() == '':
                missing.append(field)
        
        return (len(missing) == 0, missing)

# Instancia global
text_analyzer = TextAnalyzer()
