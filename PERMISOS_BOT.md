# 🔐 PERMISOS NECESARIOS PARA SELENE

Este documento detalla todos los permisos que necesita el bot Selene en cada grupo/canal.

---

## 📍 GRUPO PRINCIPAL (ID: -1003758751452)

### ✅ Permisos Obligatorios

El bot **DEBE ser administrador** con los siguientes permisos:

#### **1. Gestión de Mensajes**
- ✅ **Eliminar mensajes** - Para borrar mensajes con links, spam, palabras prohibidas
- ✅ **Leer mensajes** - Para monitorear el grupo y detectar infracciones
- ✅ **Enviar mensajes** - Para enviar avisos en #administracion
- ✅ **Enviar archivos multimedia** - Para enviar imágenes de bienvenida (Fase 3)

#### **2. Gestión de Usuarios**
- ✅ **Restringir miembros** - Para aplicar mutes (silenciar usuarios)
- ✅ **Banear usuarios** - Para expulsar usuarios que lleguen a 4 warnings o riesgo alto
- ✅ **Invitar usuarios** - Para poder desbanear (kick temporal por foto)

#### **3. Información de Usuarios**
- ✅ **Ver información de miembros** - Para verificar fotos de perfil, usernames, etc.

#### **4. Permisos NO Necesarios** (puedes desactivarlos)
- ❌ Cambiar información del grupo
- ❌ Fijar mensajes
- ❌ Agregar administradores
- ❌ Gestionar videochats
- ❌ Publicar en el canal (si el grupo tiene canal vinculado)

---

## 📍 GRUPO DE RESPALDO (ID: -1003825278496)

### ✅ Permisos Obligatorios

El bot **DEBE ser administrador** con los siguientes permisos:

#### **1. Gestión de Mensajes**
- ✅ **Eliminar mensajes** - Para borrar mensajes con links, spam, palabras prohibidas
- ✅ **Leer mensajes** - Para monitorear el grupo
- ✅ **Enviar mensajes** - Para enviar avisos
- ✅ **Enviar archivos multimedia** - Para backup y bienvenidas

#### **2. Gestión de Usuarios**
- ✅ **Restringir miembros** - Para aplicar mutes
- ✅ **Banear usuarios** - Para expulsar usuarios
- ✅ **Invitar usuarios** - Para desbanear

#### **3. Información de Usuarios**
- ✅ **Ver información de miembros** - Para verificar fotos de perfil

---

## 📢 CANAL DE ALERTAS (ID: 37738)

### ✅ Permisos Obligatorios

El bot **DEBE ser administrador** con:

- ✅ **Publicar mensajes** - Para enviar alertas de moderación
- ✅ **Editar mensajes** - Para actualizar alertas si es necesario

### ❌ Permisos NO Necesarios
- ❌ Eliminar mensajes
- ❌ Invitar usuarios
- ❌ Cambiar información del canal

---

## 📚 CANAL DE BACKUP - BIBLIOTECA ESPAÑOL (ID: 18459)

### ✅ Permisos Obligatorios

El bot **DEBE ser administrador** con:

- ✅ **Publicar mensajes** - Para hacer backup de mensajes de biblioteca
- ✅ **Enviar archivos multimedia** - Para reenviar PDFs, imágenes, etc.

### ❌ Permisos NO Necesarios
- ❌ Eliminar mensajes
- ❌ Editar mensajes
- ❌ Invitar usuarios

---

## 📚 CANAL DE BACKUP - BIBLIOTECA INGLÉS (ID: 13612)

### ✅ Permisos Obligatorios

El bot **DEBE ser administrador** con:

- ✅ **Publicar mensajes** - Para hacer backup de mensajes de biblioteca
- ✅ **Enviar archivos multimedia** - Para reenviar PDFs, imágenes, etc.

### ❌ Permisos NO Necesarios
- ❌ Eliminar mensajes
- ❌ Editar mensajes
- ❌ Invitar usuarios

---

## 📋 RESUMEN DE PERMISOS POR GRUPO/CANAL

### **Grupos Principales (ambos):**
```
✅ Eliminar mensajes
✅ Leer mensajes
✅ Enviar mensajes
✅ Enviar archivos multimedia
✅ Restringir miembros
✅ Banear usuarios
✅ Invitar usuarios
✅ Ver información de miembros
```

### **Canal de Alertas:**
```
✅ Publicar mensajes
✅ Editar mensajes
```

### **Canales de Backup (ambos):**
```
✅ Publicar mensajes
✅ Enviar archivos multimedia
```

---

## 🔧 CÓMO CONFIGURAR LOS PERMISOS

### **Para los Grupos:**

1. Ve al grupo en Telegram
2. Toca el nombre del grupo → **Administradores**
3. Busca a **Selene** en la lista de administradores
4. Si no está, toca **Agregar administrador** y busca `@tu_bot_username`
5. Activa estos permisos:
   - ✅ Eliminar mensajes
   - ✅ Restringir miembros
   - ✅ Banear usuarios
   - ✅ Invitar usuarios vía enlace
6. Guarda los cambios

### **Para el Canal de Alertas:**

1. Ve al canal en Telegram
2. Toca el nombre del canal → **Administradores**
3. Agrega a Selene como administrador
4. Activa estos permisos:
   - ✅ Publicar mensajes
   - ✅ Editar mensajes de otros
5. Guarda los cambios

### **Para los Canales de Backup:**

1. Ve al canal en Telegram
2. Toca el nombre del canal → **Administradores**
3. Agrega a Selene como administrador
4. Activa estos permisos:
   - ✅ Publicar mensajes
5. Guarda los cambios

---

## ⚠️ IMPORTANTE

### **Sin estos permisos, el bot NO podrá:**

❌ **Sin "Eliminar mensajes":**
- No podrá borrar links, spam, palabras prohibidas
- Solo detectará pero no actuará

❌ **Sin "Restringir miembros":**
- No podrá aplicar mutes (silenciar usuarios)
- Los castigos progresivos no funcionarán

❌ **Sin "Banear usuarios":**
- No podrá expulsar usuarios con 4 warnings
- No podrá banear por palabras graves
- No podrá expulsar por foto faltante

❌ **Sin "Ver información de miembros":**
- No podrá verificar si tienen foto de perfil
- No podrá detectar usuarios sospechosos

❌ **Sin "Publicar mensajes" en canales:**
- No podrá enviar alertas
- No podrá hacer backup de biblioteca

---

## 🧪 VERIFICAR PERMISOS

Una vez configurados los permisos, puedes verificar que todo funciona:

### **1. Prueba de Eliminación de Mensajes**
- Envía un mensaje con un link en el grupo
- El bot debe detectarlo y borrarlo
- Si no lo borra, falta el permiso "Eliminar mensajes"

### **2. Prueba de Alertas**
- Envía un link en el grupo
- Revisa tu canal de alertas (ID: 37738)
- Debes recibir una alerta estructurada
- Si no llega, falta el permiso "Publicar mensajes" en el canal

### **3. Prueba de Backup**
- Envía un PDF en #biblioteca español
- Revisa el canal de backup (ID: 18459)
- El mensaje debe aparecer allí
- Si no aparece, falta el permiso "Publicar mensajes" en el canal

---

## 📞 SOLUCIÓN DE PROBLEMAS

### **"El bot no borra mensajes"**
→ Verifica que tenga el permiso "Eliminar mensajes" en el grupo

### **"El bot no puede mutear usuarios"**
→ Verifica que tenga el permiso "Restringir miembros"

### **"El bot no puede banear usuarios"**
→ Verifica que tenga el permiso "Banear usuarios"

### **"No llegan alertas al canal privado"**
→ Verifica que el bot sea administrador del canal con permiso "Publicar mensajes"

### **"No se hace backup de la biblioteca"**
→ Verifica que el bot sea administrador de los canales de backup

---

## ✅ CHECKLIST FINAL

Antes de activar el modo producción, verifica:

- [ ] Bot es administrador en grupo principal (-1003758751452)
- [ ] Bot es administrador en grupo de respaldo (-1003825278496)
- [ ] Bot es administrador en canal de alertas (37738)
- [ ] Bot es administrador en canal backup español (18459)
- [ ] Bot es administrador en canal backup inglés (13612)
- [ ] Todos los permisos necesarios están activados
- [ ] Pruebas de eliminación, mute y alertas funcionan
- [ ] Modo del bot está en "prueba" para testing inicial

---

**Una vez verificado todo, usa `/modo produccion` para activar el bot completamente.**
