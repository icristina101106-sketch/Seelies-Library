
import os

filepath = r"C:\Users\icris\OneDrive\Documents\Bot Telegram\app.py"
with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

replacement = """
    from telegram import BotCommand
    commands = [
        BotCommand("buscar", "Encuentra tu proximo libro"),
        BotCommand("directorio", "Explora el indice de autores"),
        BotCommand("pedir", "Pide un libro que no encuentres"),
        BotCommand("clasicos", "Busca libros clasicos (<1950)"),
        BotCommand("lanzamientos", "Busca libros recientes"),
        BotCommand("topaportadores", "Ranking de la comunidad"),
        BotCommand("ayuda", "Manual interactivo del bot")
    ]
    try:
        await application.bot.set_my_commands(commands)
    except Exception as e:
        print(f"Error seteando comandos: {e}")
        
    print(f"Modo prueba: {config.TEST_MODE_ACTIVE}")
"""

import re
content = re.sub(r'print\(f"Modo prueba: \{config.TEST_MODE_ACTIVE\}"\)' , replacement.strip(), content)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
