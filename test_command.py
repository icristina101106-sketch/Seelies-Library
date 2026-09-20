"""
Test simple para verificar handlers
"""
import sys
sys.path.insert(0, r'c:\Users\icris\Documents\Bot Telegram')

import config
from handlers.commands import cmd_pedidoincorrecto

print("Config ADMIN_IDS:", config.ADMIN_IDS)
print("Function loaded:", cmd_pedidoincorrecto)
print("\nTest completado - la función se importa correctamente")
