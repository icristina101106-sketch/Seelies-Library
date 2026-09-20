# 🌙 SELENE - Sistema de Moderación para Telegram

Sistema completo de moderación y administración inteligente para grupos de Telegram con gestión de biblioteca, pedidos de libros y moderación automatizada.

---

## 📋 Características Implementadas (Fase 1)

### ✅ Moderación Automática
- Detección y eliminación de links (incluyendo ocultos, t.me, acortadores)
- Detección de spam/flood (10 mensajes en 10 segundos)
- Detección de mensajes repetidos (elimina desde la 4ª repetición)
- Sistema de palabras prohibidas (3 niveles: leve, media, grave)
- Detección de archivos sospechosos (.apk, .zip, .exe)
- Detección de reenvíos masivos
- Detección de invitaciones a otros grupos
- Detección básica de tono agresivo

### ✅ Sistema de Warnings
- Acumulación permanente de warnings
- 2 warnings = mute 1 hora
- 4 warnings = ban automático
- Flood: 2 advertencias en 20-30 min = ban directo
- Comando `/forgive` para revocar warnings

### ✅ Sistema de Riesgo
- Score interno (visible solo para admin)
- Puntos por eventos (link +2, flood +2, palabra grave +6, etc.)
- Estados: nuevo → normal → observado → sospechoso
- Riesgo no baja hasta ser trusted
- Trusted: riesgo baja con el tiempo

### ✅ Gestión de Usuarios
- Estados: nuevo, normal, observado, sospechoso, trusted
- Trusted automático a los 2 meses + manual con `/trust`
- Pérdida de trusted tras 3 warnings (reversible)
- Detección de usuarios sospechosos (sin foto, sin username, nombre raro)
- Sistema de foto de perfil (24h deadline, recordatorio 12h, expulsión)

### ✅ Backup de Biblioteca
- Backup automático de "biblioteca español" y "biblioteca inglés"
- Reenvío a canales de backup
- Registro en base de datos

### ✅ Sistema de Alertas
- Alertas estructuradas al canal privado
- Formato detallado con usuario, motivo, acción, warnings, riesgo

### ✅ Modos del Bot
- **Producción**: Activo, aplica castigos
- **Prueba**: Detecta pero no castiga (para testing)
- **Silencioso**: Actúa sin mensajes visibles

---

## 🚀 Instalación

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar IDs

Los IDs ya están configurados en `config.py`:
- ✅ ADMIN_ID
- ✅ GROUP_ID
- ✅ Canales de backup
- ✅ Temas del grupo

### 3. Ejecutar el Bot

```bash
python selene_bot.py
```

---

## 📝 Comandos Admin

Todos estos comandos solo pueden ser usados por el admin (ID: 1950304369)

### Gestión de Usuarios
- `/checkuser <user_id>` - Ver información completa de usuario
- `/history <user_id>` - Ver historial de acciones
- `/trust <user_id>` - Promover a trusted
- `/untrust <user_id>` - Quitar trusted

### Moderación Manual
- `/warn <user_id> [razón]` - Advertencia manual
- `/mute <user_id> <minutos>` - Mutear usuario
- `/unmute <user_id>` - Desmutear usuario
- `/ban <user_id> [razón]` - Banear usuario

### Sistema de Warnings y Riesgo
- `/forgive <warning_id>` - Perdonar warning
- `/setrisk <user_id> <puntos>` - Ajustar riesgo manualmente

### Configuración
- `/config` - Ver configuración actual
- `/modo <produccion|prueba|silencioso>` - Cambiar modo del bot

---

## ⚙️ Configuración Actual

### Tiempos
- Deadline foto de perfil: **24 horas**
- Recordatorio foto: **12 horas**
- Promoción a trusted: **60 días**
- Reset warnings trusted: **14 días**

### Umbrales
- Max warnings antes de ban: **4**
- Flood warnings antes de ban: **2**
- Umbral riesgo para ban: **13**
- Umbral riesgo sospechoso: **8**

### Duración de Mutes
- Mute 1: **60 minutos** (1 hora)
- Mute 2: **360 minutos** (6 horas)
- Mute 3: **1440 minutos** (24 horas)

### Detección de Flood
- **10 mensajes** en **10 segundos**

### Mensajes Repetidos
- Elimina desde la **4ª repetición**

---

## 🎯 Puntos de Riesgo

| Evento | Puntos |
|--------|--------|
| Sin foto | +3 |
| Sin username | +2 |
| Nombre raro | +2 |
| Link | +2 |
| Link (usuario nuevo) | +3 extra |
| Spam | +1 |
| Flood | +2 |
| Repetición | +1 |
| Palabra leve | +1 |
| Palabra media | +3 |
| Palabra grave | +6 |
| Reenvío masivo | +2 |
| Archivo sospechoso | +3 |
| Invitación a grupo | +4 |
| Combinación peligrosa | +3 |

---

## 📊 Estados de Usuario

### nuevo
- Recién entrado
- Alta vigilancia
- Riesgo no baja

### normal
- Usuario estable
- Sin alertas significativas

### observado
- Tiene algunas alertas
- Vigilancia aumentada

### sospechoso
- Múltiples alertas
- Vigilancia máxima
- Cerca del ban

### trusted
- 2 meses en grupo
- Buen comportamiento
- Warnings se resetean cada 2 semanas
- Riesgo baja con el tiempo

---

## 🔄 Tareas Automáticas

### Cada minuto
- Verificar tareas programadas pendientes

### Cada 12 horas
- Enviar recordatorio de foto de perfil

### Cada 24 horas
- Expulsar usuarios sin foto
- Reducir riesgo de usuarios trusted

### Cada 2 semanas (Domingo 00:00)
- Resetear warnings de usuarios trusted

### Diario
- Verificar promociones a trusted

---

## 📁 Estructura del Proyecto

```
Bot Telegram/
├── selene_bot.py              # Archivo principal
├── config.py                  # Configuración
├── requirements.txt           # Dependencias
├── database/
│   ├── models.py              # Esquema de BD
│   └── db_manager.py          # Gestor de BD
├── modules/
│   ├── moderation.py          # Moderación automática
│   ├── warnings.py            # Sistema de warnings
│   ├── risk.py                # Sistema de riesgo
│   ├── users.py               # Gestión de usuarios
│   ├── library.py             # Backup de biblioteca
│   └── scheduler.py           # Tareas programadas
├── handlers/
│   ├── messages.py            # Handler de mensajes
│   └── commands.py            # Handler de comandos
├── utils/
│   ├── text_analysis.py       # Análisis de texto
│   └── formatters.py          # Formateadores
└── data/
    ├── selene.db              # Base de datos
    ├── backups/               # Backups
    ├── exports/               # Reportes
    └── logs/                  # Logs
```

---

## 🗄️ Base de Datos

El sistema usa SQLite con 15 tablas:

1. **users** - Información de usuarios
2. **warnings** - Registro de advertencias
3. **risk_events** - Eventos de riesgo
4. **moderation_actions** - Acciones de moderación
5. **book_requests** - Pedidos de libros (Fase 2)
6. **request_warnings** - Warnings por pedidos (Fase 2)
7. **library_backup** - Backup de biblioteca
8. **duplicate_files** - Duplicados detectados (Fase 4)
9. **appeals** - Apelaciones (Fase 5)
10. **user_reports** - Reportes de usuarios (Fase 5)
11. **learning_cases** - Casos de aprendizaje (Fase 5)
12. **forbidden_words** - Palabras prohibidas
13. **config** - Configuración dinámica
14. **scheduled_tasks** - Tareas programadas
15. **weekly_stats** - Estadísticas semanales (Fase 5)

---

## 🧪 Modo Prueba

Para probar el bot sin aplicar castigos reales:

```bash
# En Telegram, usa:
/modo prueba
```

En modo prueba:
- ✅ Detecta todas las infracciones
- ✅ Registra en base de datos
- ✅ Envía alertas
- ❌ NO aplica castigos (no mute, no ban, no kick)
- ℹ️ Muestra mensaje: "[MODO PRUEBA] Acción que se habría tomado: ..."

Para volver a modo producción:
```bash
/modo produccion
```

---

## 📈 Próximas Fases

### Fase 2: Sistema de Pedidos (Pendiente)
- Formulario guiado por privado
- Publicación automática en #peticiones
- Comandos de pedido incorrecto
- Notificación cuando esté listo
- Eliminación automática a las 24h

### Fase 3: Bienvenidas y Onboarding (Pendiente)
- Bienvenida estética en #general
- Mensaje privado automático con menú
- Sistema FAQ completo

### Fase 4: Detección de Duplicados (Pendiente)
- Escaneo de biblioteca
- Comparación de archivos
- Reporte de duplicados

### Fase 5: Aprendizaje y Reportes (Pendiente)
- Sistema de apelaciones
- Reportes de usuarios
- Aprendizaje supervisado
- Reportes semanales

---

## ⚠️ Importante

- El bot está en **MODO PRUEBA** por defecto
- Todas las detecciones funcionan pero NO se aplican castigos
- Revisa las alertas en tu canal privado
- Usa `/modo produccion` cuando estés listo para activar los castigos reales

---

## 🆘 Solución de Problemas

### El bot no responde
- Verifica que el token sea correcto
- Verifica que el bot tenga permisos de administrador en el grupo
- Revisa los logs en `data/logs/selene.log`

### No se detectan infracciones
- Verifica que estés en modo producción o prueba (no silencioso)
- Verifica que los IDs de temas sean correctos
- Revisa las alertas en tu canal privado

### Errores de base de datos
- Elimina `data/selene.db` y reinicia el bot
- La base de datos se recreará automáticamente

---

## 📞 Soporte

Para cualquier duda o problema, revisa:
1. Los logs en `data/logs/selene.log`
2. Las alertas en tu canal privado
3. Usa `/config` para ver la configuración actual
4. Usa `/checkuser` para ver el estado de un usuario

---

**Desarrollado con 🌙 por una ingeniera**
