# Bounce Drive Media Studio

App interna para Bounce pensada para equipo: toma una carpeta compartida de Google Drive como biblioteca, deja elegir assets rápido desde web o celular, permite poner texto arriba y prepara la salida para TikTok.

## Qué hace ahora

- Lee una carpeta raíz de Google Drive y recorre subcarpetas.
- Lista imágenes y videos en una sola biblioteca.
- Tiene búsqueda, filtros y ruleta.
- Carga preview sin descarga manual.
- Exporta imágenes a `PNG` y videos a `WEBM` desde el navegador.
- Guarda configuración compartida del equipo en `studio-config.json`.
- Trae una base real para TikTok:
  - estado de conexión
  - OAuth callback
  - backend para subir videos
  - caption + hashtags + menciones
  - modos `Direct post` e `Inbox draft`

## Lo importante sobre TikTok

La integración ya quedó preparada en código, pero para funcionar de verdad todavía necesitás:

- un dominio `HTTPS`
- una app en TikTok for Developers
- `client key`
- `client secret`
- redirect URI registrado en TikTok

Además:

- `Direct post` es el modo donde el caption/hashtags salen desde la web.
- `Inbox draft` manda el video al inbox de TikTok para terminarlo ahí.
- para clientes no auditados, TikTok puede restringir la visibilidad pública
- la integración actual de esta web está enfocada en `video`
- para fotos/carruseles, TikTok pide URLs verificadas por dominio

## Archivos clave

- `index.html`: interfaz principal
- `app.css`: estilos responsive/mobile-first
- `app.js`: lógica de Drive, export, móvil y TikTok
- `server.py`: servidor local + config compartida + endpoints TikTok
- `studio-secrets.example.json`: ejemplo de credenciales server-side
- `terms.html` / `privacy.html`: legales

## Requisitos

- Python 3
- un Google OAuth Client ID de tipo `Web application`
- Google Drive API activada en tu proyecto de Google Cloud

## Setup de Google

1. Entrá a Google Cloud Console.
2. Activá `Google Drive API`.
3. Creá un OAuth Client ID de tipo `Web application`.
4. En local agregá este origin:
   - `http://localhost:8000`
5. Si el proyecto está en modo testing, agregá como `Test users` a quienes vayan a usar la app.

## Setup de TikTok

1. Copiá `studio-secrets.example.json`.
2. Renombralo a `.studio-secrets.json`.
3. Completá:

```json
{
  "tiktokClientKey": "tu-client-key",
  "tiktokClientSecret": "tu-client-secret",
  "tiktokRedirectUri": "https://tu-dominio.com/api/tiktok/callback"
}
```

Notas:

- ese archivo queda del lado servidor
- no va al frontend
- el redirect URI debe ser `HTTPS`

## Cómo correrla

1. Abrí esta carpeta en terminal.
2. Ejecutá:

```bash
python server.py
```

3. Abrí:
   - `http://localhost:8000`

El servidor escucha en `0.0.0.0`, así que también te sirve mejor para red local o para probar desde otros dispositivos en la misma red, si exponés el puerto correctamente.

## Flujo recomendado para el equipo

1. Guardar configuración compartida:
   - nombre del equipo
   - Google Client ID
   - carpeta de Drive
   - `Public Base URL` cuando la app ya esté hosteada
2. Conectar Google Drive.
3. Cargar biblioteca.
4. Buscar asset o usar ruleta.
5. Ajustar texto y encuadre.
6. Exportar.
7. Si TikTok ya está configurado:
   - conectar cuenta
   - elegir modo de publicación
   - completar caption / hashtags / menciones
   - subir

## Lo que no pude validar end-to-end

- OAuth real de Google con tu cuenta
- OAuth real de TikTok
- publicación real a TikTok

Eso no está probado porque faltan tus credenciales y un dominio HTTPS real. Pero la estructura ya quedó armada para enchufarlo sin rehacer la app.
