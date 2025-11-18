# 🛒 Cisnatura E-Commerce API

API REST para tienda en línea construida con **FastAPI**, **PostgreSQL**, **Redis** y **Docker**.

## ✨ Características

- ✅ **Autenticación JWT** con verificación de email
- ✅ **Gestión de productos** con categorías e imágenes
- ✅ **Optimización automática de imágenes** a WebP
- ✅ **Sistema de roles** (usuario/administrador)
- ✅ **Envío de emails** SMTP con templates HTML
- ✅ **Cache con Redis**
- ✅ **Base de datos PostgreSQL**
- ✅ **Docker Compose** para desarrollo
- ⏳ **Carrito de compras** (en desarrollo)
- ⏳ **Órdenes y pagos** con Stripe (en desarrollo)

---

## 🏗️ Arquitectura

```
api-cisnatura/
├── app/
│   ├── core/               # Configuración y utilidades
│   │   ├── config.py       # Variables de entorno
│   │   ├── database.py     # Conexión a PostgreSQL
│   │   ├── security.py     # JWT y hashing
│   │   ├── email_service.py # Envío de emails
│   │   ├── storage.py      # Manejo de archivos
│   │   └── dependencies.py # Dependencias de autenticación
│   ├── models/             # Modelos SQLAlchemy
│   │   ├── user.py
│   │   ├── products.py
│   │   ├── email_verification.py
│   │   └── ...
│   ├── schemas/            # Schemas Pydantic
│   │   └── auth.py
│   ├── routes/             # Endpoints de la API
│   │   ├── auth.py         # Autenticación
│   │   ├── products.py     # Productos
│   │   └── uploads.py      # Subida de imágenes
│   ├── scripts/            # Scripts de utilidad
│   │   ├── init_db.py      # Inicializar DB
│   │   └── seed_db.py      # Datos de prueba
│   ├── uploads/            # Archivos subidos (volumen Docker)
│   └── main.py             # Aplicación principal
├── docker-compose.dev.yml  # Desarrollo
├── docker-compose.yml      # Producción
├── Dockerfile
├── Makefile                # Comandos útiles
├── requirements.txt        # Dependencias Python
├── .env.example            # Variables de entorno de ejemplo
├── AUTH.md                 # Documentación de autenticación
└── UPLOADS.md              # Documentación de uploads
```

---

## 🚀 Inicio Rápido

### 1. Clonar el repositorio

```bash
git clone https://github.com/Maskeit/api-cisnatura.git
cd api-cisnatura
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

**Variables importantes:**

```bash
# JWT
SECRET_KEY=genera-una-clave-segura-con-openssl-rand-hex-32

# SMTP (Gmail)
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password-de-google

# Frontend
FRONTEND_URL=http://localhost:3000
```

### 3. Iniciar servicios

```bash
# Construir e iniciar contenedores
make dev-build

# Inicializar base de datos
make db-init

# Ver logs
make logs
```

### 4. Acceder a la API

- **API**: http://localhost:8000
- **Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📚 Documentación

### Endpoints Principales

#### Autenticación

```bash
POST /auth/register           # Registrar usuario
POST /auth/login              # Iniciar sesión
POST /auth/verify-email       # Verificar email
POST /auth/resend-verification # Reenviar email de verificación
GET  /auth/me                 # Obtener perfil (requiere auth)
```

#### Productos

```bash
GET    /products              # Listar productos (público)
GET    /products/{id}         # Ver producto (público)
GET    /products/slug/{slug}  # Ver producto por slug (público)
POST   /products              # Crear producto (admin)
PUT    /products/{id}         # Actualizar producto (admin)
DELETE /products/{id}         # Eliminar producto (admin)
```

#### Uploads

```bash
POST   /uploads/products/{id}/image      # Subir imagen de producto (admin)
POST   /uploads/categories/{id}/image    # Subir imagen de categoría (admin)
DELETE /uploads/products/{id}/image      # Eliminar imagen (admin)
GET    /static/products/{filename}.webp  # Acceder a imagen (público)
```

### Documentación Detallada

- **[AUTH.md](AUTH.md)** - Sistema de autenticación completo
- **[UPLOADS.md](UPLOADS.md)** - Manejo de imágenes y archivos

---

## 🛠️ Comandos del Makefile

### Desarrollo

```bash
make dev                # Iniciar servicios
make dev-build          # Construir e iniciar
make dev-down           # Detener servicios
make logs               # Ver logs de todos los servicios
make logs-app           # Ver logs solo de la app
```

### Base de Datos

```bash
make db                 # Conectar a PostgreSQL
make db-init            # Inicializar tablas
make db-reset           # Resetear base de datos (¡cuidado!)
make db-seed            # Poblar con datos de prueba
make db-help            # Ayuda de comandos psql
```

### Otros

```bash
make redis              # Conectar a Redis CLI
make clean              # Eliminar todo (incluyendo volúmenes)
```

---

## 🔐 Autenticación

El sistema usa **JWT (JSON Web Tokens)** con verificación de email obligatoria.

### Flujo de Registro

1. Usuario se registra → Se crea con `email_verified=False`
2. Se envía email con token de verificación (expira en 24h)
3. Usuario hace clic en el link del email
4. `email_verified=True` → Ahora puede hacer login

### Ejemplo de Uso

```python
# 1. Registrarse
response = requests.post("http://localhost:8000/auth/register", json={
    "email": "usuario@ejemplo.com",
    "password": "MiPassword123",
    "full_name": "Juan Pérez"
})

# 2. Verificar email (token del correo)
requests.post("http://localhost:8000/auth/verify-email", json={
    "token": "TOKEN_DEL_EMAIL"
})

# 3. Login
response = requests.post("http://localhost:8000/auth/login", json={
    "email": "usuario@ejemplo.com",
    "password": "MiPassword123"
})
token = response.json()["access_token"]

# 4. Usar token en peticiones
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/auth/me", headers=headers)
```

Ver [AUTH.md](AUTH.md) para documentación completa.

---

## 🖼️ Manejo de Imágenes

Todas las imágenes se optimizan automáticamente a **WebP** con:
- Compresión de ~60-70%
- Redimensionamiento a max 1920px
- Nombres únicos (UUID)
- Almacenamiento persistente en volumen Docker

### Ejemplo de Subida

```bash
curl -X POST "http://localhost:8000/uploads/products/1/image" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@imagen.jpg"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Imagen subida exitosamente",
  "data": {
    "product_id": 1,
    "image_url": "ca2cdd9f-4d2b-4ff8-a790-7508edabb2b1.webp",
    "full_url": "/static/products/ca2cdd9f-4d2b-4ff8-a790-7508edabb2b1.webp"
  }
}
```

Ver [UPLOADS.md](UPLOADS.md) para documentación completa.

---

## 🧪 Testing

```bash
# Crear usuario de prueba
docker exec -it cisnatura_app_dev python -c "
from core.database import SessionLocal
from core.security import hash_password
from models.user import User

db = SessionLocal()
user = User(
    email='test@ejemplo.com',
    hashed_password=hash_password('Test123456'),
    full_name='Usuario Test',
    email_verified=True
)
db.add(user)
db.commit()
print('✅ Usuario creado')
"

# Crear admin
docker exec -it cisnatura_app_dev python -c "
from core.database import SessionLocal
from core.security import hash_password
from models.user import User

db = SessionLocal()
admin = User(
    email='admin@cisnatura.com',
    hashed_password=hash_password('Admin123'),
    full_name='Administrador',
    is_admin=True,
    email_verified=True
)
db.add(admin)
db.commit()
print('✅ Admin creado')
"
```

---

## 🔧 Configuración SMTP (Gmail)

1. Ve a **[Google Account](https://myaccount.google.com/)**
2. **Seguridad** → Activa **Verificación en dos pasos**
3. **Seguridad** → **Contraseñas de aplicaciones**
4. Genera contraseña para "Correo"
5. Usa esa contraseña en `SMTP_PASSWORD`

```bash
# .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=abcd-efgh-ijkl-mnop  # Contraseña de aplicación
```

---

## 🌐 Despliegue (Producción)

### Docker Compose

```bash
# Usar docker-compose.yml (producción)
docker compose -f docker-compose.yml up -d --build
```

### Variables de Entorno Críticas

```bash
# Generar clave secreta segura
openssl rand -hex 32

# .env (producción)
SECRET_KEY=clave-generada-con-openssl
DATABASE_URL=postgresql://user:pass@db:5432/cisnatura
FRONTEND_URL=https://tu-dominio.com
SMTP_USER=noreply@tu-dominio.com
CORS_ALLOW_ORIGINS=https://tu-dominio.com
```

### Recomendaciones

- ✅ Usar **HTTPS** (Nginx reverse proxy + Let's Encrypt)
- ✅ Variables de entorno seguras (no hardcodear)
- ✅ Backup automático de PostgreSQL
- ✅ Rate limiting (Nginx o middleware)
- ✅ Monitoreo (Sentry, DataDog, etc.)
- ✅ CDN para imágenes (CloudFlare R2, AWS S3)

---

## 🤝 Contribuir

1. Fork del proyecto
2. Crear rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Add: nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

---

## 📄 Licencia

Este proyecto es privado. © 2025 Cisnatura

---

## 📧 Contacto

- **GitHub**: [@Maskeit](https://github.com/Maskeit)
- **Proyecto**: [api-cisnatura](https://github.com/Maskeit/api-cisnatura)

---

## 🗺️ Roadmap

### ✅ Completado
- [x] Sistema de autenticación con JWT
- [x] Verificación de email
- [x] CRUD de productos y categorías
- [x] Upload de imágenes con optimización WebP
- [x] Roles de usuario (admin/user)

### 🚧 En Desarrollo
- [ ] Carrito de compras
- [ ] Sistema de órdenes
- [ ] Integración con Stripe
- [ ] Recuperación de contraseña
- [ ] Refresh tokens

### 📋 Futuro
- [ ] Wishlist
- [ ] Reviews y ratings
- [ ] Sistema de cupones
- [ ] Notificaciones push
- [ ] OAuth (Google, Facebook)
- [ ] 2FA (Two-Factor Authentication)
- [ ] API de reportes y analytics
