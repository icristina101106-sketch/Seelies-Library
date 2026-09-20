"""
Migración para agregar tabla audit_log
"""
import aiosqlite
import config

async def migrate():
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Verificar si la tabla existe
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
        ) as cursor:
            if await cursor.fetchone():
                print("Tabla audit_log ya existe")
                return
        
        # Crear tabla audit_log
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
        
        # Crear índices
        await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_admin ON audit_log(admin_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_log(target_user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
        
        await db.commit()
        print("✅ Tabla audit_log creada correctamente")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate())
