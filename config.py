"""
ConfiguraciÃƒÂ³n central de Seelie
Todos los parÃƒÂ¡metros configurables del bot
"""

# ===== TOKEN DEL BOT =====
BOT_TOKEN = "8765952498:AAEF_Jdps0V5tKgQQQ3O5VoQL4znuwlXK0k"

# ===== IDS DE TELEGRAM =====

# Admin
ADMIN_ID = 1950304369  # Admin principal (puede reorganizar biblioteca)
ADMIN_IDS = [1950304369]  # Lista de TODOS los admins (backup + comandos)

# Grupos
GROUP_ID = -1003758751452          # Grupo principal
GROUP_NAME = "Seelie's Library"   # Nombre del grupo para mensajes
GROUP_RESPALDO_ID = -1003825278496 # Grupo de respaldo

# Alertas (en grupo de respaldo)
ALERT_GROUP_ID = GROUP_RESPALDO_ID  # Grupo donde estÃƒÂ¡n las alertas
ALERT_TOPIC_ID = 37738              # Tema de Alertas en grupo de respaldo

# Temas de Backup en Grupo de Respaldo
BACKUP_GROUP_ID = GROUP_RESPALDO_ID
BACKUP_BIBLIOTECA_ESP_TOPIC = 18459  # Tema "Biblioteca ESP" en grupo respaldo
BACKUP_BIBLIOTECA_ING_TOPIC = 13612  # Tema "Biblioteca ENG" en grupo respaldo

# Temas (Topics) del Grupo Principal
TOPIC_ADMINISTRACION = 19462  # Avisos de Seelie a miembros
TOPIC_PETICIONES = 3          # Solicitudes de libros
TOPIC_BIBLIOTECA_ESP = 4      # Biblioteca en espaÃƒÂ±ol
TOPIC_BIBLIOTECA_ING = 5      # Biblioteca en inglÃƒÂ©s
TOPIC_GENERAL = None            # General no usa thread_id en la API

# ===== CONFIGURACIÃƒâ€œN DE MODERACIÃƒâ€œN =====

# Tiempos (en horas)
PHOTO_DEADLINE_HOURS = 24
PHOTO_REMINDER_HOURS = 12
REQUEST_AUTO_DELETE_HOURS = 24
TRUSTED_PROMOTION_DAYS = 60
WARNING_RESET_DAYS = 14  # Solo para trusted

# Umbrales de Warnings
MAX_WARNINGS_BEFORE_BAN = 4
FLOOD_WARNINGS_BEFORE_BAN = 2
FLOOD_TIME_WINDOW_MINUTES = 30

# DuraciÃƒÂ³n de Mutes (en minutos)
MUTE_DURATION_1 = 60      # 1 hora
MUTE_DURATION_2 = 360     # 6 horas
MUTE_DURATION_3 = 1440    # 24 horas

# Sistema de Riesgo
RISK_SCORE_BAN_THRESHOLD = 13
RISK_SCORE_SUSPICIOUS_THRESHOLD = 8
RISK_SCORE_OBSERVED_THRESHOLD = 4

# Puntos de Riesgo por Evento
RISK_POINTS = {
    'sin_foto': 3,
    'sin_username': 2,
    'nombre_raro': 2,
    'link': 2,
    'new_user_link': 3,  # Extra para usuarios nuevos
    'spam': 1,
    'flood': 2,
    'repeticion': 1,
    'palabra_leve': 1,
    'palabra_media': 3,
    'palabra_grave': 6,
    'reenvio_masivo': 2,
    'archivo_sospechoso': 3,
    'invitacion_grupo': 4,
    'combinacion_peligrosa': 3
}

# Flood Detection
FLOOD_MESSAGE_COUNT = 10
FLOOD_TIME_SECONDS = 10

# Mensajes Repetidos
REPEATED_MESSAGE_THRESHOLD = 4

# ===== MODOS DEL BOT =====
MODE = "produccion"  # "produccion", "prueba", "silencioso"
TEST_MODE_ACTIVE = False
SILENT_MODE_ACTIVE = False

# ===== CONFIGURACIÃƒâ€œN DE TRUSTED =====
TRUSTED_AUTO_PROMOTION = True
TRUSTED_WARNINGS_TO_LOSE = 3
TRUSTED_REQUIREMENTS = {
    'days_in_group': 60,
    'max_warnings': 3,
    'max_risk': 5,
    'has_photo': True,
    'never_banned': True
}

# ===== CONFIGURACIÃƒâ€œN DE USUARIOS NUEVOS =====
NEW_USER_WATCH_MINUTES = 60
NEW_USER_SUSPICIOUS_CHECKS = [
    'sin_foto',
    'sin_username',
    'nombre_raro',
    'mensaje_rapido'
]

# ===== MENSAJES DEL BOT =====
BOT_TONE = "neutral"  # "amable", "neutral", "estricto"
SHOW_REASON_IN_MESSAGES = True
SHOW_USER_NAME_IN_OWN_MESSAGE = False

# ===== BACKUP Y REPORTES =====
AUTO_BACKUP_DATABASE = True
BACKUP_FREQUENCY_DAYS = 1
WEEKLY_REPORT_DAY = 6  # 0=Lunes, 6=Domingo
WEEKLY_REPORT_HOUR = 23
WEEKLY_MAINTENANCE_DAY = 'sun'
WEEKLY_MAINTENANCE_HOUR = 3

# ===== BIBLIOTECA / TELEGRAM =====
# LÃƒÂ­mite de descarga de bots (Telegram). Archivos mÃƒÂ¡s grandes se dejan sin renombrar.
TELEGRAM_BOT_DOWNLOAD_LIMIT = 20 * 1024 * 1024
JOIN_REQUEST_TIMEOUT_HOURS = 24

# ===== APRENDIZAJE SUPERVISADO =====
LEARNING_ENABLED = True
REQUIRE_ADMIN_DECISION_FOR_AMBIGUOUS = True

# ===== FORMATO DE PEDIDOS =====
REQUEST_FORMAT = {
    'titulo': True,
    'autor': True,
    'idioma': True,
    'formato': True
}

# ===== DETECCIÃƒâ€œN DE DUPLICADOS =====
DUPLICATE_SIMILARITY_THRESHOLD = 0.85  # 85% de similitud

# ===== LOGS =====
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = "data/logs/selene.log"

# ===== BASE DE DATOS =====
DATABASE_PATH = "data/selene.db"

# ===== PATHS =====
DATA_DIR = "data"
BACKUPS_DIR = "data/backups"
EXPORTS_DIR = "data/exports"
LOGS_DIR = "data/logs"
ASSETS_DIR = "assets"
WELCOME_IMAGES_DIR = "assets/welcome_images"
VACATION_TOLERANCE_MULTIPLIER = 2


TOPIC_AYUDA = 99999 # Tema de ayuda (cambiar a real)



