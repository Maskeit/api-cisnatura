# Sistema de Autenticación con JWT y Verificación de Email

## 🏗️ Arquitectura

El sistema de autenticación está completamente implementado con las siguientes características:

### ✅ Características Implementadas

- **Registro de usuarios** con validación de contraseñas fuertes
- **Verificación de email** con tokens seguros (expiran en 24h)
- **Login con JWT** (access_token + refresh_token)
- **Protección de rutas** con dependencias de FastAPI
- **Roles de usuario** (admin/usuario normal)
- **Envío de emails** con templates HTML profesionales

---

## 📁 Estructura de Archivos

```
app/
├── models/
│   ├── user.py                      # Modelo User con email_verified
│   └── email_verification.py        # Tokens de verificación
├── schemas/
│   └── auth.py                      # Pydantic schemas
├── core/
│   ├── security.py                  # Hashing passwords + JWT
│   ├── email_service.py             # Envío de emails SMTP
│   ├── dependencies.py              # get_current_user, get_current_admin_user
│   ├── config.py                    # Variables de entorno
│   └── database.py                  # Conexión DB
└── routes/
    └── auth.py                      # Endpoints de autenticación
```

---

## 🔐 Endpoints de Autenticación

### 1. Registrar Usuario

```http
POST /auth/register
Content-Type: application/json

{
  "email": "usuario@ejemplo.com",
  "password": "MiPassword123",
  "full_name": "Juan Pérez"
}
```

**Validaciones de contraseña:**
- Mínimo 8 caracteres
- Al menos 1 número
- Al menos 1 mayúscula
- Al menos 1 minúscula

**Respuesta:**
```json
{
  "success": true,
  "status_code": 201,
  "message": "Usuario registrado exitosamente. Revisa tu correo para verificar tu cuenta.",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "usuario@ejemplo.com",
    "email_verified": false
  }
}
```

**Flujo:**
1. Usuario se registra
2. Se crea en DB con `email_verified=False`
3. Se genera token de verificación (expira en 24h)
4. Se envía email con link de confirmación

---

### 2. Verificar Email

```http
POST /auth/verify-email
Content-Type: application/json

{
  "token": "TOKEN_RECIBIDO_POR_EMAIL"
}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Email verificado exitosamente. Ya puedes iniciar sesión.",
  "data": {
    "email_verified": true
  }
}
```

**El token:**
- Es un string seguro de 32 bytes (64 caracteres)
- Expira en 24 horas
- Solo se puede usar una vez
- Se invalida después de usarse

---

### 3. Reenviar Email de Verificación

```http
POST /auth/resend-verification
Content-Type: application/json

{
  "email": "usuario@ejemplo.com"
}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Email de verificación enviado."
}
```

---

### 4. Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "usuario@ejemplo.com",
  "password": "MiPassword123"
}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Login exitoso",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "usuario@ejemplo.com",
      "full_name": "Juan Pérez",
      "is_active": true,
      "is_admin": false,
      "email_verified": true
    }
  }
}
```

**Validaciones:**
- Email y contraseña correctos
- Usuario activo (`is_active=True`)
- **Email verificado** (`email_verified=True`) ⚠️

**JWT Payload:**
```json
{
  "sub": "USER_ID",
  "email": "usuario@ejemplo.com",
  "is_admin": false,
  "exp": 1234567890,
  "iat": 1234567890,
  "type": "access",
  "jti": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Nota:** El campo `jti` (JWT ID) es un identificador único del token usado para el sistema de logout/blacklist.

---

### 5. Obtener Perfil del Usuario

```http
GET /auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Respuesta:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "usuario@ejemplo.com",
  "full_name": "Juan Pérez",
  "is_active": true,
  "is_admin": false,
  "email_verified": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 6. Logout (Cerrar Sesión)

```http
POST /auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Sesión cerrada exitosamente"
}
```

**Flujo:**
1. El token se agrega a una **blacklist en Redis**
2. El token permanece inválido hasta su expiración natural
3. Todas las peticiones futuras con ese token serán rechazadas con error `TOKEN_REVOKED`
4. El usuario debe hacer login nuevamente para obtener un nuevo token

**Seguridad:**
- El token no se puede usar nuevamente después del logout
- La blacklist se almacena en Redis con TTL igual al tiempo restante de expiración del token
- Cuando el token expira naturalmente, se elimina automáticamente de Redis

---

## 🔒 Proteger Endpoints

### Usuario Autenticado

```python
from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models.user import User

router = APIRouter()

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Solo usuarios autenticados pueden acceder"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name
    }
```

### Solo Administradores

```python
from core.dependencies import get_current_admin_user

@router.post("/products")
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """Solo administradores pueden crear productos"""
    # current_user.is_admin == True garantizado
    pass
```

### Usuario Opcional (Público pero Personalizable)

```python
from typing import Optional
from core.dependencies import get_optional_current_user

@router.get("/products")
async def list_products(
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Endpoint público, pero cambia si hay usuario autenticado"""
    if current_user:
        # Mostrar precios con descuento para usuarios registrados
        discount = 0.10
    else:
        # Precios normales para visitantes
        discount = 0
```

---

## 📧 Configuración de Email (SMTP)

### Desarrollo con MailHog (Recomendado)

MailHog es un servidor SMTP de pruebas que captura todos los emails y los muestra en una interfaz web.

```bash
# Ya está configurado en docker-compose.dev.yml
# El archivo .env ya tiene la configuración correcta:
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=

# Iniciar servicios (incluye MailHog)
make dev-build

# Abrir interfaz web de MailHog
make mailhog
# O manualmente: http://localhost:8025
```

**Características de MailHog:**
- ✅ No requiere credenciales
- ✅ Captura todos los emails enviados
- ✅ Interfaz web para ver los emails
- ✅ Perfecto para desarrollo y testing
- ✅ Los emails nunca se envían realmente

### Producción con Gmail

Para producción, configura Gmail en tu `.env`:

```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
FROM_EMAIL=noreply@cisnatura.com
FROM_NAME=Cisnatura

# Frontend URL (para links de verificación)
FRONTEND_URL=https://tu-dominio.com
```

### 🔧 Configurar Gmail para SMTP

1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. **Seguridad** → **Verificación en dos pasos** (actívala)
3. **Seguridad** → **Contraseñas de aplicaciones**
4. Genera una contraseña para "Correo"
5. Usa esa contraseña en `SMTP_PASSWORD`

### 📮 Templates de Email

El sistema incluye templates HTML profesionales:

#### Email de Verificación
- Diseño moderno con gradientes
- Botón call-to-action destacado
- Link alternativo en texto plano
- Nota de expiración (24h)

#### Email de Recuperación de Contraseña
- Similar al de verificación
- Expira en 1 hora
- Incluye advertencia de seguridad

---

## 🗃️ Estructura de Base de Datos

### Tabla `users`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### Tabla `email_verification_tokens`

```sql
CREATE TABLE email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🚀 Inicializar Base de Datos

```bash
# 1. Reconstruir contenedor con nuevas dependencias
make dev-build

# 2. Inicializar tablas
make db-init

# 3. (Opcional) Crear usuario admin de prueba
docker exec -it cisnatura_app_dev python -c "
from core.database import SessionLocal
from core.security import hash_password
from models.user import User

db = SessionLocal()

admin = User(
    email='admin@cisnatura.com',
    hashed_password=hash_password('Admin123'),
    full_name='Administrador',
    is_active=True,
    is_admin=True,
    email_verified=True
)

db.add(admin)
db.commit()
print('✅ Usuario admin creado')
"
```

---

## 🧪 Probar el Sistema

### 1. Registrar Usuario

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@ejemplo.com",
    "password": "Test123456",
    "full_name": "Usuario Test"
  }'
```

### 2. Verificar Email

```bash
# Obtener token del email recibido
curl -X POST "http://localhost:8000/auth/verify-email" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TOKEN_AQUI"
  }'
```

### 3. Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@ejemplo.com",
    "password": "Test123456"
  }'
```

### 4. Usar el Token

```bash
# Guardar el access_token de la respuesta anterior
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Acceder a endpoint protegido
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔐 Seguridad

### ✅ Implementado

- ✅ Contraseñas hasheadas con bcrypt
- ✅ JWT firmados con HS256 con JTI único
- ✅ Tokens de verificación seguros (32 bytes)
- ✅ Expiración de tokens
- ✅ Validación de contraseñas fuertes
- ✅ Blacklist de tokens con Redis (logout)
- ✅ Verificación de email obligatoria
- ✅ Protección de rutas con dependencias
- ✅ HTTPS en producción (recomendado)

### 🛡️ Recomendaciones Adicionales

1. **Cambiar SECRET_KEY en producción**
   ```bash
   # Generar clave segura
   openssl rand -hex 32
   ```

2. **Rate Limiting** (pendiente)
   - Limitar intentos de login
   - Limitar envío de emails

3. **2FA / MFA** (futuro)
   - Autenticación de dos factores

---

## 📱 Integración con Frontend (Next.js)

### Configuración

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Ejemplo de Registro

```typescript
// app/auth/register/page.tsx
async function handleRegister(data: RegisterForm) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  const result = await response.json();
  
  if (result.success) {
    // Mostrar mensaje: "Revisa tu correo"
    router.push('/auth/verify-pending');
  }
}
```

### Ejemplo de Login

```typescript
// app/auth/login/page.tsx
async function handleLogin(credentials: LoginForm) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials)
  });
  
  const result = await response.json();
  
  if (response.ok) {
    // Guardar tokens
    localStorage.setItem('access_token', result.access_token);
    localStorage.setItem('refresh_token', result.refresh_token);
    
    router.push('/dashboard');
  }
}
```

### Ejemplo de Petición Autenticada

```typescript
// utils/api.ts
async function fetchWithAuth(url: string, options = {}) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.status === 401) {
    // Token expirado, redirigir a login
    localStorage.clear();
    router.push('/auth/login');
  }
  
  return response;
}
```

---

## 🐛 Troubleshooting

### Error: "Token inválido o expirado"
- Verifica que el token sea correcto
- Verifica que no haya expirado (30 minutos por defecto)
- Genera un nuevo token haciendo login nuevamente

### Error: "Email no verificado"
- El usuario debe verificar su email antes de hacer login
- Reenviar email de verificación con `/auth/resend-verification`

### No llegan los emails
- Verifica configuración SMTP en `.env`
- Revisa logs del contenedor: `make logs-app`
- Verifica que Gmail permita "aplicaciones menos seguras" o usa "contraseña de aplicación"

### Error al crear tablas
```bash
# Reiniciar base de datos
make db-reset
```

---

## 📊 Flujo Completo

```mermaid
sequenceDiagram
    actor Usuario
    participant Frontend
    participant API
    participant DB
    participant Email

    Usuario->>Frontend: Registrarse
    Frontend->>API: POST /auth/register
    API->>DB: Crear usuario (email_verified=false)
    API->>DB: Crear token de verificación
    API->>Email: Enviar email con link
    API->>Frontend: 201 Created
    
    Usuario->>Email: Abrir email
    Email->>Usuario: Click en link
    Usuario->>Frontend: /auth/verify?token=XXX
    Frontend->>API: POST /auth/verify-email
    API->>DB: Validar token
    API->>DB: Actualizar user.email_verified=true
    API->>Frontend: 200 OK
    
    Usuario->>Frontend: Login
    Frontend->>API: POST /auth/login
    API->>DB: Validar credenciales + email_verified
    API->>Frontend: JWT tokens
    Frontend->>Frontend: Guardar tokens
    
    Usuario->>Frontend: Ver productos
    Frontend->>API: GET /products (con token)
    API->>API: Validar JWT
    API->>DB: Query productos
    API->>Frontend: Productos
```

---

## 🎯 Próximos Pasos (Opcional)

1. **Recuperación de contraseña** (email con token)
2. **Refresh token endpoint** (renovar access_token sin re-autenticar)
3. **Rate limiting** con Redis (prevenir fuerza bruta)
4. **OAuth** (Google, Facebook)
5. **2FA** (TOTP con Google Authenticator)

---

## 📝 Notas Finales

- ✅ Los tokens JWT se invalidan al hacer logout (blacklist en Redis)
- ✅ La blacklist expira automáticamente cuando el token expira naturalmente
- ✅ Los emails se envían de forma asíncrona
- ✅ Todos los endpoints retornan formato consistente con `success`, `status_code`, `message`, `data`
- ✅ El sistema está listo para producción con configuración SMTP de Gmail
