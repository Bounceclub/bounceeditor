# Bounce Editor - Android App

Esta es la versión Android de Bounce Editor, creada con Capacitor.

## Estructura del proyecto

- `www/` - Archivos web (HTML, CSS, JS)
- `android/` - Proyecto Android nativo
- `capacitor.config.json` - Configuración de Capacitor

## Comandos útiles

### Sincronizar archivos web con Android
```bash
npm run cap:sync
```

### Abrir proyecto en Android Studio
```bash
npm run cap:open
```

### Compilar APK de debug
```bash
npm run cap:build
```

### Instalar en dispositivo conectado
```bash
npm run cap:install
```

## Configuración

La app está configurada para usar el servidor en Render:
- URL: `https://bounceeditor.onrender.com`
- App ID: `com.bounce.editor`
- App Name: `BounceEditor`

## Requisitos para compilar

- Node.js
- Android Studio
- SDK de Android (API nivel 33 o superior)
- Java JDK 11 o superior

## Generar APK release

1. Abrir Android Studio: `npm run cap:open`
2. Build → Generate Signed Bundle / APK
3. Elegir "APK"
4. Crear o usar keystore existente
5. Seleccionar "release" y firmar

## Notas importantes

- La app usa el servidor en Render, no necesita backend local
- Los archivos web se sincronizan automáticamente con `npm run cap:sync`
- Para cambios en el frontend, copiar los archivos a `www/` y sincronizar