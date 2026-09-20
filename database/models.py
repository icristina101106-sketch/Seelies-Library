"""
Esquema de base de datos para Seelie
Define todas las tablas y sus relaciones
"""

import os
import sqlite3
import aiosqlite
from datetime import datetime
import config

class Database:
    def __init__(self, db_path=config.DATABASE_PATH):
        self.db_path = db_path
    
    async def init(self):
        """Inicializar BD y datos base (usado por app.py)."""
        os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        await self.init_database()
        await self.populate_forbidden_words()

    async def init_database(self):
        """Inicializa todas las tablas de la base de datos"""
        async with aiosqlite.connect(self.db_path) as db:
            # Tabla: users
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'nuevo',
                    has_photo BOOLEAN DEFAULT FALSE,
                    photo_deadline TIMESTAMP,
                    photo_reminder_sent BOOLEAN DEFAULT FALSE,
                    invited_by INTEGER,
                    warnings_count INTEGER DEFAULT 0,
                    risk_score INTEGER DEFAULT 0,
                    last_warning_date TIMESTAMP,
                    last_risk_update TIMESTAMP,
                    trusted_date TIMESTAMP,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_date TIMESTAMP,
                    notes TEXT,
                    contributions INTEGER DEFAULT 0,
                    FOREIGN KEY (invited_by) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: warnings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    warning_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message_text TEXT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    topic_id INTEGER,
                    action_taken TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    revoked BOOLEAN DEFAULT FALSE,
                    revoked_by INTEGER,
                    revoked_date TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: risk_events
            await db.execute("""
                CREATE TABLE IF NOT EXISTS risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    risk_points INTEGER NOT NULL,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: moderation_actions
            await db.execute("""
                CREATE TABLE IF NOT EXISTS moderation_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    reason TEXT,
                    duration INTEGER,
                    message_deleted TEXT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    topic_id INTEGER,
                    auto_action BOOLEAN DEFAULT TRUE,
                    admin_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: book_requests
            await db.execute("""
                CREATE TABLE IF NOT EXISTS book_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    language TEXT NOT NULL,
                    format TEXT NOT NULL,
                    status TEXT DEFAULT 'pendiente',
                    request_method TEXT,
                    message_id INTEGER,
                    published_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_date TIMESTAMP,
                    auto_delete_scheduled TIMESTAMP,
                    deleted BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: request_warnings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS request_warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    warning_type TEXT NOT NULL,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES book_requests(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: bot_settings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                )
            """)
            
            # Tabla: config_log
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    setting_key TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla: forbidden_books
            await db.execute("""
                CREATE TABLE IF NOT EXISTS forbidden_books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    reason TEXT,
                    added_by INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla: request_waitlist
            await db.execute("""
                CREATE TABLE IF NOT EXISTS request_waitlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES book_requests(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(request_id, user_id)
                )
            """)
            
            # Tabla: library_backup
            await db.execute("""
                CREATE TABLE IF NOT EXISTS library_backup (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_name TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER,
                    content_type TEXT,
                    file_name TEXT,
                    file_id TEXT,
                    file_size INTEGER,
                    caption TEXT,
                    text_content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    backup_channel_msg_id INTEGER
                )
            """)
            
            # Tabla: duplicate_files
            await db.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name_1 TEXT NOT NULL,
                    file_name_2 TEXT NOT NULL,
                    message_id_1 INTEGER NOT NULL,
                    message_id_2 INTEGER NOT NULL,
                    similarity_score REAL,
                    match_type TEXT,
                    reviewed BOOLEAN DEFAULT FALSE,
                    action_taken TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla: appeals
            await db.execute("""
                CREATE TABLE IF NOT EXISTS appeals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    appeal_type TEXT NOT NULL,
                    related_action_id INTEGER,
                    reason TEXT,
                    conversation TEXT,
                    status TEXT DEFAULT 'pendiente',
                    admin_decision TEXT,
                    admin_notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_date TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: user_reports
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id INTEGER NOT NULL,
                    reported_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    evidence TEXT,
                    message_id INTEGER,
                    status TEXT DEFAULT 'pendiente',
                    admin_notes TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_date TIMESTAMP,
                    FOREIGN KEY (reporter_id) REFERENCES users(user_id),
                    FOREIGN KEY (reported_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: learning_cases
            await db.execute("""
                CREATE TABLE IF NOT EXISTS learning_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_type TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    user_id INTEGER,
                    admin_decision TEXT NOT NULL,
                    context TEXT,
                    apply_future BOOLEAN DEFAULT TRUE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: forbidden_words
            await db.execute("""
                CREATE TABLE IF NOT EXISTS forbidden_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL UNIQUE,
                    severity TEXT NOT NULL,
                    action TEXT NOT NULL,
                    is_regex BOOLEAN DEFAULT FALSE,
                    active BOOLEAN DEFAULT TRUE,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla: config
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla: scheduled_tasks
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    target_id INTEGER,
                    execute_at TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_date TIMESTAMP,
                    extra_data TEXT
                )
            """)
            
            # Tabla: audit_log (log de auditoría de acciones admin)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    admin_id INTEGER NOT NULL,
                    admin_username TEXT,
                    action_type TEXT NOT NULL,
                    target_user_id INTEGER,
                    target_username TEXT,
                    reason TEXT,
                    details TEXT,
                    chat_id INTEGER,
                    message_id INTEGER
                )
            """)
            
            # Tabla: weekly_stats
            await db.execute("""
                CREATE TABLE IF NOT EXISTS weekly_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_start DATE NOT NULL,
                    week_end DATE NOT NULL,
                    new_members INTEGER DEFAULT 0,
                    members_no_photo INTEGER DEFAULT 0,
                    total_warnings INTEGER DEFAULT 0,
                    total_mutes INTEGER DEFAULT 0,
                    total_bans INTEGER DEFAULT 0,
                    suspicious_users INTEGER DEFAULT 0,
                    new_trusted INTEGER DEFAULT 0,
                    incorrect_requests INTEGER DEFAULT 0,
                    appeals_received INTEGER DEFAULT 0,
                    duplicates_found INTEGER DEFAULT 0,
                    report_file_path TEXT,
                    generated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla: invite_links
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invite_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link TEXT NOT NULL UNIQUE,
                    creator_id INTEGER NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uses INTEGER DEFAULT 0,
                    max_uses INTEGER DEFAULT 1,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                )
            """)
            
            # Tabla: join_requests (filtro de admisión)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS join_requests (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    PRIMARY KEY (user_id, chat_id)
                )
            """)
            
            # Crear índices para mejorar rendimiento
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_trusted ON users(trusted_date)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_warnings_user ON warnings(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_warnings_timestamp ON warnings(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_risk_user ON risk_events(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_moderation_user ON moderation_actions(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_requests_user ON book_requests(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON book_requests(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_library_topic ON library_backup(topic_name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON scheduled_tasks(status)")
            
            # Migraciones automáticas
            try:
                await db.execute("ALTER TABLE library_backup ADD COLUMN original_year INTEGER")
            except Exception:
                pass # La columna ya existe
            
            try:
                await db.execute("ALTER TABLE library_backup ADD COLUMN genre TEXT")
            except Exception:
                pass # La columna ya existe
                
            try:
                await db.execute("ALTER TABLE library_backup ADD COLUMN page_count INTEGER")
            except Exception:
                pass # La columna ya existe
                
            try:
                await db.execute("ALTER TABLE library_backup ADD COLUMN forwards_count INTEGER DEFAULT 0")
            except Exception:
                pass # La columna ya existe
            
            try:
                await db.execute("ALTER TABLE users ADD COLUMN is_trusted BOOLEAN DEFAULT FALSE")
            except Exception:
                pass # La columna ya existe
                
            try:
                await db.execute("ALTER TABLE users ADD COLUMN rank INTEGER DEFAULT 0")
            except Exception:
                pass # La columna ya existe
                
            try:
                await db.execute("ALTER TABLE users ADD COLUMN message_count INTEGER DEFAULT 0")
            except Exception:
                pass # La columna ya existe
            
            await db.commit()
            
        print("OK - Base de datos inicializada correctamente")
    
    async def populate_forbidden_words(self):
        """Poblar tabla de palabras prohibidas con las palabras iniciales"""
        forbidden_words_data = [
            # Graves
            ("chinga tu madre", "grave", "ban", False),
            ("vete a la verga", "grave", "ban", False),
            ("hijo de puta", "grave", "ban", False),
            ("vales verga", "grave", "ban", False),
            ("ojalá te mueras", "grave", "ban", False),
            ("ojalá te mueras", "grave", "ban", False),
            
            # Medias
            ("pendejo", "media", "mute_1h", False),
            ("pendeja", "media", "mute_1h", False),
            ("idiota", "media", "mute_1h", False),
            ("imbécil", "media", "mute_1h", False),
            ("imbecil", "media", "mute_1h", False),
            ("estúpido", "media", "mute_1h", False),
            ("estupido", "media", "mute_1h", False),
            ("pinche idiota", "media", "mute_1h", False),
            ("cabrón", "media", "mute_1h", False),
            ("cabron", "media", "mute_1h", False),
            ("no vales nada", "media", "mute_1h", False),
            ("das asco", "media", "mute_1h", False),
            
            # Leves
            ("menso", "leve", "warning", False),
            ("mensa", "leve", "warning", False),
            ("tonto", "leve", "warning", False),
            ("tonta", "leve", "warning", False),
            ("tont@", "leve", "warning", False),
            ("baboso", "leve", "warning", False),
            ("ridículo", "leve", "warning", False),
            ("ridiculo", "leve", "warning", False),
            ("fastidioso", "leve", "warning", False),
            ("castroso", "leve", "warning", False),
            ("inútil", "leve", "warning", False),
            ("inutil", "leve", "warning", False),
            ("necio", "leve", "warning", False),
            ("payaso", "leve", "warning", False),
        ]
        
        async with aiosqlite.connect(self.db_path) as db:
            for word, severity, action, is_regex in forbidden_words_data:
                await db.execute("""
                    INSERT OR IGNORE INTO forbidden_words (word, severity, action, is_regex)
                    VALUES (?, ?, ?, ?)
                """, (word, severity, action, is_regex))
            await db.commit()
        
        print("OK - Palabras prohibidas cargadas")

# Instancia global
db = Database()
