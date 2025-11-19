# Sistema de Manejo de Imágenes

## 📁 Arquitectura

El sistema de almacenamiento de imágenes está diseñado para:
- **Optimización automática**: Todas las imágenes se convierten a WebP
- **Persistencia**: Los archivos se guardan en un volumen Docker
- **Servicio estático**: FastAPI sirve las imágenes directamente
- **Escalabilidad**: Preparado para migrar a CDN (S3, Cloudflare, etc.)

## 🗂️ Estructura de Archivos

```
/app/uploads/              (Volumen Docker persistente)
├── products/              Imágenes de productos
│   ├── uuid-1.webp
│   ├── uuid-2.webp
│   └── ...
└── categories/            Imágenes de categorías
    ├── uuid-1.webp
    ├── uuid-2.webp
    └── ...
```

## 🚀 Configuración

### Variables de Entorno

```bash
UPLOAD_DIR=/app/uploads                    # Directorio de uploads
MAX_UPLOAD_SIZE=5242880                    # 5MB en bytes
ALLOWED_EXTENSIONS=jpg,jpeg,png,webp       # Extensiones permitidas
WEBP_QUALITY=85                            # Calidad WebP (1-100)
```

### Docker Compose

El volumen `uploads_data` está configurado en `docker-compose.dev.yml`:

```yaml
volumes:
  - uploads_data:/app/uploads
```

Esto asegura que:
- ✅ Las imágenes persisten aunque el contenedor se reinicie
- ✅ No se pierden al hacer rebuild
- ✅ Se pueden hacer backups del volumen

## 📡 Endpoints de API

### 1. Subir Imagen de Producto

```http
POST /uploads/products/{product_id}/image
Content-Type: multipart/form-data

Body:
  file: (archivo de imagen)
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Imagen subida exitosamente",
  "data": {
    "product_id": 1,
    "image_url": "/static/products/550e8400-e29b-41d4-a716-446655440000.webp"
  }
}
```

### 2. Subir Imagen de Categoría

```http
POST /uploads/categories/{category_id}/image
Content-Type: multipart/form-data

Body:
  file: (archivo de imagen)
```

### 3. Eliminar Imagen de Producto

```http
DELETE /uploads/products/{product_id}/image
```

### 4. Acceder a Imágenes (GET estático)

```http
GET /static/products/{filename}.webp
GET /static/categories/{filename}.webp
```

## 🖼️ Proceso de Optimización

Cuando se sube una imagen:

1. **Validación**:
   - Verifica que sea un archivo de imagen válido
   - Comprueba la extensión (jpg, jpeg, png, webp)
   - Valida el tamaño (máx 5MB)

2. **Optimización**:
   - Convierte a formato WebP
   - Ajusta calidad al 85% (configurable)
   - Redimensiona si excede 1920px en el lado más largo
   - Convierte RGBA/transparencias a RGB con fondo blanco

3. **Almacenamiento**:
   - Genera UUID único como nombre
   - Guarda en `/app/uploads/products/` o `/categories/`
   - Elimina imagen anterior si existe

4. **Actualización BD**:
   - Guarda la ruta relativa en la tabla
   - Ejemplo: `/static/products/uuid.webp`

## 🧪 Probar el Sistema

### Desde cURL

```bash
# Subir imagen de producto
curl -X POST "http://localhost:8000/uploads/products/1/image" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/ruta/a/imagen.jpg"

# Ver imagen subida
curl "http://localhost:8000/static/products/550e8400-e29b-41d4-a716-446655440000.webp" \
  --output imagen.webp

# Eliminar imagen
curl -X DELETE "http://localhost:8000/uploads/products/1/image"
```

### Desde Python

```python
import requests

# Subir imagen
url = "http://localhost:8000/uploads/products/1/image"
files = {"file": open("producto.jpg", "rb")}
response = requests.post(url, files=files)
print(response.json())

# URL de la imagen
image_url = response.json()["data"]["image_url"]
full_url = f"http://localhost:8000{image_url}"
```

### Desde JavaScript/Frontend

```javascript
// Subir imagen
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/uploads/products/1/image', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log(data);

// Usar imagen en HTML
const imageUrl = data.data.image_url;
document.querySelector('img').src = `http://localhost:8000${imageUrl}`;
```

## 🔧 Comandos Útiles

### Ver volumen de uploads

```bash
# Listar volúmenes
docker volume ls | grep uploads

# Inspeccionar volumen
docker volume inspect api-cisnatura_uploads_data

# Ver contenido (desde el contenedor)
docker exec -it cisnatura_app_dev ls -lh /app/uploads/products/
docker exec -it cisnatura_app_dev ls -lh /app/uploads/categories/
```

### Backup de imágenes

```bash
# Crear backup del volumen
docker run --rm \
  -v api-cisnatura_uploads_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/uploads-backup.tar.gz -C /data .

# Restaurar backup
docker run --rm \
  -v api-cisnatura_uploads_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/uploads-backup.tar.gz -C /data
```

### Limpiar imágenes huérfanas

```bash
# Desde el contenedor
docker exec -it cisnatura_app_dev python -c "
from core.storage import storage_service
from core.database import SessionLocal
from models.products import Product, Category

db = SessionLocal()

# Obtener todas las URLs de imágenes en la BD
product_images = {p.image_url for p in db.query(Product).all() if p.image_url}
category_images = {c.image_url for c in db.query(Category).all() if c.image_url}
all_images = product_images | category_images

# Listar archivos físicos
import os
from pathlib import Path
upload_dir = Path('/app/uploads')
physical_files = set()
for subdir in ['products', 'categories']:
    dir_path = upload_dir / subdir
    if dir_path.exists():
        physical_files.update(f'/static/{subdir}/{f.name}' for f in dir_path.iterdir())

# Encontrar huérfanas
orphaned = physical_files - all_images
print(f'Archivos huérfanos: {len(orphaned)}')
for f in orphaned:
    print(f)
"
```

## 🔒 Seguridad

**Implementado:**
- ✅ Validación de tipo de archivo (solo imágenes)
- ✅ Validación de extensiones permitidas
- ✅ Límite de tamaño (5MB)
- ✅ Nombres únicos (UUID) para prevenir colisiones
- ✅ Conversión forzada a formato seguro (WebP)

**TODO (requiere autenticación):**
- ⏳ Solo administradores pueden subir/eliminar imágenes
- ⏳ Rate limiting para prevenir abuso
- ⏳ Sanitización de metadatos EXIF

## 📊 Beneficios del formato WebP

| Aspecto | JPEG/PNG | WebP |
|---------|----------|------|
| Tamaño | 100% | ~30-40% |
| Calidad | Buena | Similar o mejor |
| Transparencia | PNG: Sí, JPEG: No | Sí |
| Compresión | Limitada | Avanzada |
| Compatibilidad | 100% | 95%+ (navegadores modernos) |

## 🚀 Migración Futura a CDN

El código está preparado para migrar fácilmente a un CDN:

```python
# core/storage.py - Ejemplo de adaptación para S3

class S3StorageService(StorageService):
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = settings.S3_BUCKET
    
    async def save_product_image(self, file: UploadFile) -> str:
        # ... validación y optimización igual ...
        
        # Subir a S3 en lugar de disco local
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f"products/{filename}",
            Body=optimized_content,
            ContentType="image/webp"
        )
        
        # Retornar URL del CDN
        return f"https://cdn.cisnatura.com/products/{filename}"
```

## 📝 Notas

- Las imágenes se convierten automáticamente a RGB (transparencias → fondo blanco)
- El volumen Docker persiste entre reinicios pero se pierde con `make clean`
- Para producción, considera usar un CDN externo (CloudFront, Cloudflare R2, etc.)
- Las imágenes grandes (>1920px) se redimensionan automáticamente
