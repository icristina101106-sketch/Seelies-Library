# Seelie Bot - Configuración para Railway (Hosting 24/7)

## Requisitos

1. Cuenta en Railway (railway.app) - Gratis
2. Tu BOT_TOKEN configurado en config.py

## Pasos para desplegar

### 1. Instalar Railway CLI (opcional, también puedes usar web)
```bash
npm install -g @railway/cli
```

### 2. Login en Railway
```bash
railway login
```

### 3. Crear proyecto y subir
```bash
railway init
railway up
```

O subir directamente desde la web de Railway:
- Conectar tu repo de GitHub o subir archivos

### 4. Variables de entorno (IMPORTANTE)

En Railway Dashboard → Variables, agrega:

```
PORT=5000
```

El bot usará automáticamente el puerto que Railway asigne.

### 5. Health Check

Railway verificará automáticamente:
- `GET /` → Status del bot
- `GET /health` → Health check

### 6. Ver logs

```bash
railway logs
```

## Archivos importantes

- `app.py` - Bot + servidor web para health checks
- `Procfile` - Configuración del proceso
- `requirements.txt` - Dependencias

## Notas

- El bot se reinicia automáticamente si hay errores
- Health check mantiene el servicio activo
- Base de datos SQLite se guarda en `/data` (persistente en Railway)

## URLs de monitoreo

Una vez desplegado, Railway te dará una URL como:
`https://seelie-bot.up.railway.app/`

Visitar esa URL te mostrará el status del bot.
