# 🚀 Guía de Configuración de TikTok OAuth

## ✅ Estado: Flujo de OAuth YA IMPLEMENTADO

¡Buenas noticias! Tu aplicación ya tiene todo el código necesario para el flujo de OAuth de TikTok. Solo necesitas configurar las credenciales.

---

## 🔧 Cómo Configurar TikTok OAuth

### Paso 1: Obtener Credenciales de TikTok

1. **Ve a TikTok Developer Portal**: https://developers.tiktok.com/
2. **Inicia sesión** con tu cuenta de TikTok
3. **Crea una nueva aplicación** usando la información de `TIKTOK_QUICK_START.md`
4. **Espera la aprobación** de TikTok (puede tomar días/semanas)
5. **Una vez aprobada**, obtendrás:
   - **Client Key** (ejemplo: `awx1234567890`)
   - **Client Secret** (ejemplo: `abc123def456`)

### Paso 2: Configurar Redirect URI en TikTok

En el portal de TikTok, configura:

```
Redirect URI: https://bounceeditor.onrender.com/api/tiktok/callback
```

### Paso 3: Configurar Credenciales en tu Aplicación

#### Opción A: Usar Variables de Entorno (Recomendado para Render)

En Render, configura las siguientes variables de entorno:

```
TIKTOK_CLIENT_KEY=awx1234567890
TIKTOK_CLIENT_SECRET=abc123def456
TIKTOK_REDIRECT_URI=https://bounceeditor.onrender.com/api/tiktok/callback
```

#### Opción B: Usar Archivo de Configuración

Crea el archivo `.studio-secrets.json` en tu proyecto:

```json
{
  "tiktokClientKey": "TU_CLIENT_KEY_DE_TIKTOK",
  "tiktokClientSecret": "TU_CLIENT_SECRET_DE_TIKTOK",
  "tiktokRedirectUri": "https://bounceeditor.onrender.com/api/tiktok/callback"
}
```

**⚠️ IMPORTANTE**: Reemplaza los valores de ejemplo con tus credenciales reales.

---

## 🔄 Cómo Funciona el Flujo de OAuth

### 1. Usuario hace clic en "Conectar TikTok"
- Frontend llama a `/api/tiktok/oauth/start`
- Servidor genera URL de autorización de TikTok
- Usuario es redirigido a TikTok

### 2. Usuario autoriza en TikTok
- TikTok muestra pantalla de consentimiento
- Usuario autoriza la aplicación
- TikTok redirige al callback

### 3. TikTok redirige al callback
- TikTok envía código de autorización a `/api/tiktok/callback`
- Servidor intercambia código por access token
- Token se guarda en `.tiktok-token.json`

### 4. Aplicación puede usar TikTok API
- Access token se usa para publicar videos
- Token se refresca automáticamente cuando expira

---

## 🧪 Cómo Probar el Flujo de OAuth

### 1. Configurar Credenciales
```bash
# En tu entorno local
export TIKTOK_CLIENT_KEY="tu_client_key"
export TIKTOK_CLIENT_SECRET="tu_client_secret"
export TIKTOK_REDIRECT_URI="http://localhost:8000/api/tiktok/callback"
```

### 2. Iniciar el Servidor
```bash
python server.py
```

### 3. Abrir la Aplicación
```
http://localhost:8000
```

### 4. Probar el Flujo
1. Ve a la sección "TikTok"
2. Haz clic en "Conectar TikTok"
3. Autoriza en TikTok
4. Verifica que la cuenta esté conectada

---

## 📋 Estructura del Código OAuth

### Backend (server.py)

```python
# Endpoints implementados:
POST /api/tiktok/oauth/start    # Inicia OAuth
GET  /api/tiktok/callback       # Callback de TikTok
GET  /api/tiktok/status         # Verifica estado
POST /api/tiktok/disconnect    # Desconecta cuenta
POST /api/tiktok/post           # Publica video

# Funciones implementadas:
- handle_tiktok_oauth_start()    # Inicia flujo OAuth
- handle_tiktok_callback()       # Maneja callback
- exchange_code_for_token()      # Intercambia código por token
- refresh_access_token()         # Refresca token
- ensure_access_token()          # Asegura token válido
```

### Frontend (app.js)

```javascript
// Funciones implementadas:
- connectTikTok()                # Conecta cuenta TikTok
- disconnectTikTok()             # Desconecta cuenta
- loadTikTokStatus()             # Carga estado
- publishToTikTok()              # Publica video

// Elementos del DOM:
- connectTikTokButton            # Botón conectar
- disconnectTikTokButton          # Botón desconectar
- refreshTikTokButton            # Botón actualizar
- tiktokStatusBadge              # Badge de estado
- tiktokAccountLabel             # Label de cuenta
```

---

## 🔐 Seguridad

### Tokens y Credenciales

1. **Client Secret**: NUNCA se expone al frontend
2. **Access Token**: Se guarda en el servidor (.tiktok-token.json)
3. **Refresh Token**: Se guarda en el servidor para refrescar access token
4. **State Token**: Se usa para prevenir ataques CSRF

### Archivos de Configuración

- `.studio-secrets.json`: Credenciales de TikTok (NO commit a git)
- `.tiktok-token.json`: Tokens de acceso (NO commit a git)
- `studio-secrets.example.json`: Plantilla de ejemplo (SÍ commit a git)

---

## 🚨 Problemas Comunes

### Error: "TikTok no está configurado"

**Causa**: Credenciales no configuradas
**Solución**: Configura variables de entorno o archivo .studio-secrets.json

### Error: "TikTok Login Kit web requiere redirect URI HTTPS"

**Causa**: Usando HTTP en lugar de HTTPS
**Solución**: Usa HTTPS o configura dominio con certificado SSL

### Error: "Invalid redirect_uri"

**Causa**: Redirect URI no coincide con el configurado en TikTok
**Solución**: Verifica que coincida exactamente con el portal de TikTok

### Error: "Invalid client_id or client_secret"

**Causa**: Credenciales incorrectas
**Solución**: Verifica Client Key y Client Secret en el portal de TikTok

---

## 📝 Checklist de Configuración

- [ ] Aplicación creada en TikTok Developer Portal
- [ ] Aplicación aprobada por TikTok
- [ ] Client Key obtenido
- [ ] Client Secret obtenido
- [ ] Redirect URI configurado en TikTok
- [ ] Credenciales configuradas en tu aplicación
- [ ] Servidor reiniciado con nuevas credenciales
- [ ] Flujo de OAuth probado exitosamente
- [ ] Publicación de video probada

---

## 🎯 Pasos Siguientes

1. **Completa el formulario** de TikTok Developer Portal
2. **Espera aprobación** de la aplicación
3. **Obtén credenciales** (Client Key y Client Secret)
4. **Configura credenciales** en tu aplicación
5. **Prueba el flujo** de OAuth
6. **Prueba la publicación** de videos

---

## 📞 Soporte

Si tienes problemas:

- **Documentación TikTok**: https://developers.tiktok.com/
- **Foro TikTok**: https://developers.tiktok.com/forum/
- **Email**: bouncenewchapter@gmail.com

---

## ✅ Resumen

**¡Tu aplicación YA TIENE el flujo de OAuth implementado!**

Solo necesitas:
1. Obtener credenciales de TikTok
2. Configurarlas en tu aplicación
3. Probar el flujo

Todo el código necesario ya está en su lugar. 🎉