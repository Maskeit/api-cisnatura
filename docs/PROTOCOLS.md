# Guía de Uso: Protocolos (Productos Digitales)

## 📚 Estructura Rápida

### Lo Básico

Un **Protocolo** es:
- ✅ Un producto 100% digital (sin envío)
- ✅ Contenido estructurado en **fases** (como capítulos)
- ✅ Cada fase puede tener **recursos** (imágenes, PDFs, videos, enlaces)
- ✅ El usuario accede después de comprar
- ✅ El sistema trackea el progreso del usuario

### Tablas Principales

| Tabla | Propósito |
|-------|-----------|
| `protocols` | El protocolo en sí |
| `protocol_phases` | Fases/secciones (paso 1, paso 2, etc) |
| `protocol_resources` | Recursos en cada fase (imágenes, PDFs, etc) |
| `protocol_access` | Control: quién tiene acceso a qué |
| `protocol_progress` | Seguimiento: dónde está cada usuario |

---

## 🛠️ Crear un Protocolo

### Paso 1: Crear el Producto Base

```python
# En una ruta de admin
from models.products import Product, Category

# Obtener categoría (o crear una)
category = db.query(Category).filter(
    Category.slug == "educacion"
).first()

# Crear producto (sin stock porque es digital)
product = Product(
    name="Mi Primer Protocolo",
    slug="mi-primer-protocolo",
    sku="PROTO-001",
    description="Aprende paso a paso",
    price=29.99,  # Precio del protocolo
    stock=999,  # Ilimitado para productos digitales
    category_id=category.id,
    is_active=True
)
db.add(product)
db.flush()  # Para obtener el ID
```

### Paso 2: Crear el Protocolo

```python
from models.protocols import Protocol, ProtocolPhase

protocol = Protocol(
    name="Mi Primer Protocolo",
    slug="mi-primer-protocolo",
    description="Aprende paso a paso sin salir de casa",
    long_description="Descripción larga con detalles...",
    product_id=product.id,  # ← Vincular al producto
    author="Dr. Juan Pérez",
    version="1.0",
    difficulty_level="beginner",
    estimated_duration_hours=3,
    is_featured=False,
    is_published=False  # No publicar aún
)
db.add(protocol)
db.flush()
```

### Paso 3: Crear Fases

```python
# Fase 1: Introducción
phase1 = ProtocolPhase(
    protocol_id=protocol.id,
    title="Introducción",
    slug="introduccion",
    description="Qué aprenderemos",
    content="<h2>¡Bienvenido!</h2><p>En esta fase...</p>",  # HTML
    order=1,
    duration_minutes=15,
    is_required=True
)
db.add(phase1)
db.flush()

# Fase 2: Contenido Principal
phase2 = ProtocolPhase(
    protocol_id=protocol.id,
    title="Contenido Principal",
    slug="contenido-principal",
    description="Lo más importante",
    content="<h2>Capítulo Principal</h2><p>...</p>",
    order=2,
    duration_minutes=60,
    is_required=True
)
db.add(phase2)
db.flush()
```

### Paso 4: Agregar Recursos (Opcional)

```python
from models.protocols import ProtocolResource

# Imagen en Fase 1
resource1 = ProtocolResource(
    phase_id=phase1.id,
    resource_type="image",
    title="Imagen de introducción",
    url="/static/protocols/intro.webp",
    order=0,
    is_visible=True
)
db.add(resource1)

# PDF descargable en Fase 2
resource2 = ProtocolResource(
    phase_id=phase2.id,
    resource_type="pdf",
    title="Guía en PDF",
    url="/static/protocols/guia.pdf",
    order=0,
    is_visible=True
)
db.add(resource2)

db.commit()
```

### Paso 5: Publicar

```python
protocol.is_published = True
db.commit()

# Ahora el protocolo es vendible
```

---

## 💳 Compra de Protocolo

### Flujo Automático (Con Webhook de Stripe)

```python
# Cuando el pago se completa en Stripe:

from core.protocol_service import ProtocolAccessService

# 1. Obtener la orden
order = db.query(Order).filter(Order.id == order_id).first()

# 2. Marcar como pagada
order.status = OrderStatus.PAID
db.commit()

# 3. Otorgar acceso a todos los protocolos en la orden
ProtocolAccessService.grant_protocol_access(
    order=order,
    db=db,
    access_duration_days=None  # None = acceso permanente
)

# El usuario ya tiene acceso! ✓
```

---

## 👤 Usuario Lee el Protocolo

### Usuario ve sus protocolos

```python
# GET /protocols/my-protocols/

from models.protocols import ProtocolAccess, ProtocolProgress

user_id = current_user.id

# Obtener accesos activos
accesses = db.query(ProtocolAccess).filter(
    ProtocolAccess.user_id == user_id,
    ProtocolAccess.is_active == True
).all()

# Retornar con progreso
for access in accesses:
    progress = db.query(ProtocolProgress).filter(
        ProtocolProgress.protocol_id == access.protocol_id,
        ProtocolProgress.user_id == user_id
    ).first()
    
    print(f"Protocolo: {access.protocol.name}")
    print(f"Progreso: {progress.completed_phases}/{progress.total_phases} fases")
```

### Usuario abre el protocolo

```python
# GET /protocols/{slug}/read

protocol = db.query(Protocol).filter(
    Protocol.slug == slug
).first()

# Verificar acceso
access = db.query(ProtocolAccess).filter(
    ProtocolAccess.protocol_id == protocol.id,
    ProtocolAccess.user_id == user_id,
    ProtocolAccess.is_active == True
).first()

if not access:
    raise HTTPException(status_code=403, detail="No tienes acceso")

# Actualizar "visto por última vez"
access.last_accessed_at = datetime.utcnow()
db.commit()

# Retornar protocolo con todas sus fases
return protocol  # Contiene todas las ProtocolPhase
```

### Usuario actualiza su progreso

```python
# PUT /protocols/{slug}/progress
# Body: {"current_phase_order": 2, "completed_phases": 2}

protocol = db.query(Protocol).filter(Protocol.slug == slug).first()

# Obtener o crear progreso
progress = db.query(ProtocolProgress).filter(
    ProtocolProgress.protocol_id == protocol.id,
    ProtocolProgress.user_id == user_id
).first()

if not progress:
    progress = ProtocolProgress(
        protocol_id=protocol.id,
        user_id=user_id,
        total_phases=len(protocol.phases)
    )
    db.add(progress)

# Actualizar
progress.current_phase_order = 2
progress.completed_phases = 2
progress.last_accessed_at = datetime.utcnow()

# Si completó todo
if progress.completed_phases >= progress.total_phases:
    progress.completed_at = datetime.utcnow()

db.commit()
```

---

## 🔍 Consultas Útiles

### Admin: Ver todos los protocolos

```python
protocols = db.query(Protocol).all()
for p in protocols:
    print(f"{p.name} - Publicado: {p.is_published} - Fases: {len(p.phases)}")
```

### Admin: Ver quién compró

```python
# Quién tiene acceso al protocolo ID 5
accesses = db.query(ProtocolAccess).filter(
    ProtocolAccess.protocol_id == 5
).all()

for access in accesses:
    print(f"Usuario: {access.user.email} - Acceso desde: {access.granted_at}")
```

### Usuario: Ver su progreso

```python
# Mi progreso en todos mis protocolos
progress_list = db.query(ProtocolProgress).filter(
    ProtocolProgress.user_id == current_user.id
).all()

for p in progress_list:
    pct = (p.completed_phases / p.total_phases * 100) if p.total_phases > 0 else 0
    print(f"{p.protocol.name}: {pct:.0f}% completado")
```

---

## ⏰ Acceso por Tiempo

### Dar acceso limitado (ej: 30 días)

```python
from datetime import datetime, timedelta

access_until = datetime.utcnow() + timedelta(days=30)

protocol_access = ProtocolAccess(
    protocol_id=protocol.id,
    user_id=user.id,
    order_id=order.id,
    order_item_id=order_item.id,
    access_until=access_until,  # ← Expira en 30 días
    is_active=True
)
db.add(protocol_access)
db.commit()
```

### Limpiar acceso expirado (Cron Job)

```python
from core.protocol_service import ProtocolAccessService

# Ejecutar diariamente
ProtocolAccessService.check_expired_access(db)
```

---

## 📊 Estadísticas para Admin

### Protocolo más vendido

```python
from sqlalchemy import func

best_protocol = db.query(
    Protocol.name,
    func.count(ProtocolAccess.id).label("sales")
).join(ProtocolAccess).group_by(
    Protocol.id
).order_by(func.count(ProtocolAccess.id).desc()).first()

print(f"{best_protocol.name}: {best_protocol.sales} compras")
```

### Progreso promedio

```python
avg_progress = db.query(
    func.avg(ProtocolProgress.completed_phases / ProtocolProgress.total_phases * 100)
).scalar() or 0

print(f"Progreso promedio: {avg_progress:.1f}%")
```

---

## 🎨 Tipos de Recurso

```python
class ResourceType(str, Enum):
    IMAGE = "image"      # Imágenes WebP, JPG, PNG
    PDF = "pdf"          # Documentos PDF
    VIDEO = "video"      # Videos (URL o embed)
    LINK = "link"        # Enlaces externos
    DOWNLOAD = "download"  # Descargas (ZIP, etc)
```

---

## 🚀 Checklist de Implementación

- [ ] Crear producto base
- [ ] Crear protocolo
- [ ] Agregar al menos 1 fase
- [ ] Publicar protocolo
- [ ] Probar compra
- [ ] Verificar acceso automático
- [ ] Probar lectura de protocolo
- [ ] Agregar endpoint de progreso
- [ ] Crear cron para limpiar acceso expirado
- [ ] Mostrar protocolos en tienda

---

## 📝 Notas

- Los protocolos **no requieren dirección de envío**
- El contenido está en HTML, soporta markdown convertido
- Los recursos se pueden actualizar sin afectar el producto
- El progreso se guarda automáticamente
- El acceso no se elimina, solo se marca como inactivo
