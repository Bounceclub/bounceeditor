# Solución para errores 502 con archivos MOV en Render

## Problema Identificado
Los archivos MOV estaban causando errores 502 (Bad Gateway) en el entorno de Render debido a:
- **Timeout**: El transcoding tomaba demasiado tiempo para los límites de Render
- **Memoria**: Archivos grandes excedían la memoria disponible en el servicio gratuito
- **Duración**: El preview de 60 segundos era demasiado largo para procesamiento rápido

## Soluciones Aplicadas

### 1. Optimización de Tiempo
- **Preview**: Reducido de 60s a 10s
- **Timeout**: Reducido de 10 minutos a 2 minutos
- **Preset ffmpeg**: Cambiado de 'fast' a 'ultrafast'

### 2. Optimización de Calidad
- **Video CRF**: Aumentado de 23 a 28 (menor calidad, más velocidad)
- **Audio bitrate**: Reducido de 128k a 96k
- **Threads**: Limitado a 2 hilos para eficiencia de memoria

### 3. Límites de Tamaño
- **Preview**: Máximo 100 MB
- **Exportación completa**: Máximo 500 MB

### 4. Manejo de Errores
- Detección específica de MemoryError
- Mensajes de error claros para limitaciones de Render
- Logging mejorado para diagnóstico

## Instrucciones de Uso

### Para Videos Pequeños (< 100 MB)
✅ **Preview**: Funciona correctamente
✅ **Exportación**: Funciona correctamente

### Para Videos Medianos (100-500 MB)
⚠️ **Preview**: Puede fallar con mensaje de tamaño
✅ **Exportación**: Funciona correctamente

### Para Videos Grandes (> 500 MB)
❌ **Preview**: Fallará con mensaje de tamaño
❌ **Exportación**: Fallará con mensaje de tamaño

## Recomendaciones

### 1. Para Mejor Experiencia en Render
- **Comprimir videos** antes de subirlos a Drive
- **Usar formatos MP4** en lugar de MOV cuando sea posible
- **Mantener videos bajo 100 MB** para preview rápido

### 2. Para Videos Grandes
- **Descargar directamente** desde Drive en lugar de usar preview
- **Usar exportación completa** en lugar de preview
- **Considerar servicio de pago** de Render para más recursos

### 3. Alternativas
- **Usar servidor local** para videos grandes
- **Optimizar videos** con Handbrake antes de subir
- **Dividir videos** largos en segmentos más pequeños

## Comandos Útiles

### Para Comprimir Videos (Handbrake)
```bash
# Comprimir para web (calidad media)
handbrake -i input.mov -o output.mp4 -e x264 -q 28 -B 96

# Comprimir para preview (calidad baja, rápido)
handbrake -i input.mov -o output.mp4 -e x264 -q 32 -B 64 --optimize
```

### Para Verificar Tamaño
```bash
# Ver tamaño en MB
ls -lh video.mp4

# Ver información detallada
ffprobe video.mp4
```

## Próximos Pasos

1. **Probar con videos pequeños** (< 50 MB) para verificar que funciona
2. **Monitorear logs de Render** para identificar patrones de error
3. **Considerar upgrade** de Render si se necesita procesar videos grandes regularmente
4. **Optimizar videos** antes de subirlos a Drive

## Soporte

Si los problemas persisten:
1. Revisar los logs de Render para errores específicos
2. Verificar el tamaño del archivo que está causando el error
3. Compartir el mensaje de error exacto para diagnóstico adicional

## Notas Técnicas

- **Render Free Tier**: 512 MB RAM, límites de tiempo estrictos
- **Render Paid Tier**: Más recursos disponibles
- **ffmpeg en cloud**: Requiere optimizaciones específicas para funcionar bien
- **MOV files**: A menudo usan codecs que requieren más procesamiento que MP4