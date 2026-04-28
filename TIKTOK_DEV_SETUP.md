# Configuración de TikTok for Developers - BounceClub

## Información Básica de la Aplicación

### App Icon
✅ **Ya tienes tu icono** (1024x1024px, menos de 5MB, formato PNG/JPEG)

### App Name
```
BounceClub
```

### Category
```
Entertainment
```

### Description (máximo 120 caracteres)
```
BounceClub media studio: edita, organiza y publica contenido para TikTok desde una plataforma unificada.
```

### URLs Legales
```
Terms of Service URL: https://bounceeditor.onrender.com/terms.html
Privacy Policy URL: https://bounceeditor.onrender.com/privacy.html
```

### Platforms
```
✅ Web
✅ Desktop
```

## App Review - Información Requerida

### Explicación de Productos y Scopes (máximo 1000 caracteres)

```
BounceClub Media Studio es una herramienta interna de gestión de contenido que permite al equipo de BounceClub:

1. **Video Upload Kit**: Importar videos desde Google Drive y organizarlos en una biblioteca centralizada.

2. **Content Posting API**: Publicar videos directamente en TikTok con:
   - Texto overlays personalizados
   - Captions y hashtags
   - Configuración de privacidad
   - Opciones de interacción (comentarios, duet, stitch)

3. **User Info Basic**: Obtener información básica de la cuenta de TikTok conectada para mostrar el perfil del usuario en la interfaz.

**Flujo de Integración**:
- Los usuarios conectan su cuenta de TikTok mediante OAuth 2.0
- Seleccionan videos de la biblioteca de Google Drive
- Aplican overlays de texto y configuraciones de publicación
- Publican directamente en TikTok con todos los metadatos

**Cambios en esta versión**:
- Integración completa con Google Drive API
- Mejoras en el editor de video con preview en tiempo real
- Optimización para publicaciones directas a TikTok
```

### Video de Demo (Requisitos)

**Formato**: MP4 o MOV
**Tamaño**: Máximo 50MB por video
**Cantidad**: Hasta 5 videos

**Contenido del Video**:
El video debe mostrar el flujo completo de integración con TikTok:

1. **Inicio del video**: Mostrar el sitio web `https://bounceeditor.onrender.com`

2. **Conexión con TikTok**:
   - Navegar a la sección "TikTok"
   - Hacer clic en "Conectar TikTok"
   - Mostrar el flujo de OAuth de TikTok
   - Mostrar la cuenta conectada exitosamente

3. **Selección de Video**:
   - Navegar a la biblioteca de Google Drive
   - Seleccionar un video
   - Mostrar el preview del video

4. **Edición de Contenido**:
   - Agregar texto overlay
   - Configurar caption y hashtags
   - Ajustar configuraciones de privacidad

5. **Publicación en TikTok**:
   - Hacer clic en "Subir a TikTok"
   - Mostrar el proceso de carga
   - Confirmar la publicación exitosa

6. **Verificación**: Mostrar el video publicado en la cuenta de TikTok

**Consejos para el Video**:
- Grabar la pantalla en alta calidad
- Usar un video de prueba corto (10-15 segundos)
- Asegurarse de que el dominio `bounceeditor.onrender.com` sea visible
- Mostrar claramente todos los pasos del flujo
- Incluir subtítulos si es necesario

## Products y Scopes a Configurar

### Products a Agregar:

1. **Video Upload Kit**
   - Permite subir videos a TikTok
   - Necesario para la funcionalidad principal

2. **User Info Basic**
   - Permite obtener información básica del usuario
   - Necesario para mostrar el perfil conectado

### Scopes a Agregar:

1. **user.info.basic**
   - Permite acceder a información básica del usuario
   - Incluye: display_name, avatar_url

2. **video.upload**
   - Permite subir videos a TikTok
   - Necesario para la funcionalidad de publicación

3. **video.publish**
   - Permite publicar videos en TikTok
   - Necesario para la funcionalidad principal

## URLs de Callback

### Redirect URI
```
https://bounceeditor.onrender.com/api/tiktok/callback
```

## Checklist de Preparación

### Antes de Enviar la Aplicación:

- [ ] Icono de aplicación listo (1024x1024px, <5MB)
- [ ] Nombre de aplicación: "BounceClub"
- [ ] Categoría: "Entertainment"
- [ ] Descripción completada (<120 caracteres)
- [ ] URLs de Terms of Service y Privacy Policy configuradas
- [ ] Plataformas seleccionadas (Web, Desktop)
- [ ] Explicación de productos y scopes completada (<1000 caracteres)
- [ ] Video de demo grabado (MP4/MOV, <50MB)
- [ ] Todos los productos necesarios agregados
- [ ] Todos los scopes necesarios agregados
- [ ] Redirect URI configurado correctamente

## URLs de Verificación

### Sitio Web Principal
```
https://bounceeditor.onrender.com
```

### Páginas Legales
```
Terms of Service: https://bounceeditor.onrender.com/terms.html
Privacy Policy: https://bounceeditor.onrender.com/privacy.html
```

### API Endpoints
```
Health Check: https://bounceeditor.onrender.com/api/health
Config: https://bounceeditor.onrender.com/api/config
TikTok Status: https://bounceeditor.onrender.com/api/tiktok/status
```

## Notas Importantes

1. **Dominio**: Asegúrate de que el dominio `bounceeditor.onrender.com` sea visible en el video de demo

2. **Sandbox**: Si es la primera vez que envías la aplicación, debes usar el entorno sandbox del Developer Portal

3. **Video de Demo**: El video debe mostrar el flujo completo de integración, no solo capturas estáticas

4. **Scopes**: Solo agrega los scopes que realmente necesitas. Scopes adicionales pueden retrasar el proceso de revisión

5. **Tiempo de Revisión**: El proceso de revisión puede tomar varios días o semanas

## Pasos Siguientes

1. **Completar el formulario** con la información proporcionada
2. **Grabar el video de demo** mostrando el flujo completo
3. **Subir el video** al portal de desarrolladores
4. **Enviar la aplicación** para revisión
5. **Monitorear el estado** de la aplicación en el portal
6. **Configurar las credenciales** una vez aprobada

## Contacto de Soporte

Si tienes problemas durante el proceso de configuración:

- **Email de contacto**: bouncenewchapter@gmail.com
- **Documentación de TikTok**: https://developers.tiktok.com/
- **Foro de desarrolladores**: https://developers.tiktok.com/forum/