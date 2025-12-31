# Arquitectura de Autenticación y Seguridad de Sesiones

## Resumen

Este documento describe la arquitectura de seguridad implementada para la autenticación y manejo de sesiones en Cisnatura API.

## Métodos de Autenticación Soportados

### 1. Login con Email/Contraseña
- Endpoint: `POST /auth/login`
- Valida credenciales contra la base de datos
- Requiere email verificado

### 2. Login con Google (Firebase SSO)
- Endpoint: `POST /auth/google-login`
- Token de Firebase validado en **backend** con Firebase Admin SDK
- **NUNCA** confiar solo en validación del frontend
- Después de validar Firebase, se emiten tokens JWT propios

## Arquitectura de Tokens

### Flujo de Autenticación

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │      │   Backend   │      │  Firebase   │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       │  1. Login Request  │                    │
       │ (email/pass o      │                    │
       │  Firebase token)   │                    │
       ├───────────────────►│                    │
       │                    │                    │
       │                    │ 2. Validar Firebase│
       │                    │    (si aplica)     │
       │                    ├───────────────────►│
       │                    │◄───────────────────┤
       │                    │                    │
       │ 3. Set-Cookie:     │                    │
       │    access_token    │                    │
       │    refresh_token   │                    │
       │    csrf_token      │                    │
       │◄───────────────────┤                    │
       │                    │                    │
       │ 4. Request con     │                    │
       │    cookies auto    │                    │
       ├───────────────────►│                    │
       │                    │                    │
```

### Tipos de Tokens

| Token | Tipo | Duración | Almacenamiento |
|-------|------|----------|----------------|
| `access_token` | JWT | 30 días* | Cookie HttpOnly |
| `refresh_token` | JWT | 30 días | Cookie HttpOnly |
| `csrf_token` | Random | 30 días* | Cookie (NO HttpOnly) |

*Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`

## Seguridad de Cookies

### Configuración de Cookies

```python
{
    "httponly": True,      # JavaScript NO puede acceder
    "secure": True,        # Solo HTTPS (producción)
    "samesite": "lax",     # Protección CSRF básica
    "path": "/",
    "domain": ".cisnaturatienda.com"  # Solo en producción
}
```

### ¿Por qué HttpOnly?

| Método | XSS Vulnerable | CSRF Vulnerable | Recomendación |
|--------|----------------|-----------------|---------------|
| localStorage | ✅ SÍ | ❌ NO | ⚠️ No recomendado |
| Cookie NO HttpOnly | ✅ SÍ | ✅ SÍ | ⚠️ No recomendado |
| Cookie HttpOnly | ❌ NO | ✅ SÍ* | ✅ Recomendado |

*Mitigado con SameSite y CSRF token

## Protección CSRF

### ¿Cuándo aplica?

- ✅ Si usas cookies automáticas para auth → **CSRF aplica**
- ❌ Si usas `Authorization: Bearer` exclusivamente → CSRF baja

### Implementación

1. En login, el backend genera un `csrf_token` y lo envía en cookie NO HttpOnly
2. El frontend lee ese token y lo envía en el header `X-CSRF-Token`
3. El middleware valida que ambos coincidan

```typescript
// Frontend (api.ts)
const csrfToken = Cookies.get('csrf_token');
if (csrfToken) {
  config.headers['X-CSRF-Token'] = csrfToken;
}
```

### Rutas Exentas de CSRF

```python
CSRF_EXEMPT_PATHS = {
    "/payments/webhook",       # Stripe webhook
    "/payments/stripe/webhook",
    "/auth/google-login",      # Firebase valida de otra forma
}
```

## Flujo de Autenticación Dual

El sistema soporta dos métodos simultáneamente para compatibilidad:

### 1. Cookies HttpOnly (Recomendado para Web SPA)

```typescript
// El navegador envía cookies automáticamente
const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,  // IMPORTANTE
});
```

### 2. Bearer Token (Para Apps Móviles/APIs)

```typescript
// Enviar token manualmente
const response = await fetch('/api/resource', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
```

## Endpoints de Autenticación

### POST /auth/login
Login con email y contraseña.

**Request:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "user": { ... }
  }
}
```

**Cookies establecidas:**
- `access_token` (HttpOnly)
- `refresh_token` (HttpOnly)
- `csrf_token` (legible por JS)

### POST /auth/google-login
Login con Google SSO.

**Request:**
```json
{
  "firebase_token": "eyJ..."
}
```

### POST /auth/refresh
Refrescar access token.

**Métodos soportados:**
1. Cookie HttpOnly `refresh_token` (automático)
2. Body JSON `{"refresh_token": "..."}`

### POST /auth/logout
Cerrar sesión.

**Acciones:**
1. Agrega token a blacklist en Redis
2. Elimina cookies HttpOnly
3. El token permanece inválido hasta su expiración

### GET /auth/me
Obtener usuario autenticado.

## Validación de Firebase (Google SSO)

### Proceso de Validación

```python
# El backend SIEMPRE valida con Firebase Admin SDK
from firebase_admin import auth

decoded_token = auth.verify_id_token(firebase_token)
# Extrae: uid, email, email_verified, name, picture
```

### Manejo de Errores

| Error | Código | Significado |
|-------|--------|-------------|
| `ExpiredIdTokenError` | 401 | Token expirado |
| `RevokedIdTokenError` | 401 | Token revocado |
| `InvalidIdTokenError` | 401 | Token inválido |

### Vinculación de Cuentas

Si un usuario tiene cuenta con email/password y luego intenta login con Google:
- Se vincula `firebase_uid` a la cuenta existente
- Se actualiza `auth_provider` a "google"
- Se marca email como verificado (Google ya lo verificó)

## Token Blacklist (Redis)

### Funcionamiento

```python
# Al hacer logout
TokenBlacklistService.revoke_token(
    token_jti=payload["jti"],
    expires_in_seconds=remaining_time
)

# Al validar token
if TokenBlacklistService.is_token_revoked(token_jti):
    raise HTTPException(401, "Token revocado")
```

### Claves en Redis

```
token:blacklist:{jti} -> "1" (TTL: tiempo hasta expiración)
```

## Configuración de Entorno

### Variables Requeridas

```env
# JWT
SECRET_KEY=clave-secreta-muy-segura
ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 30 días
REFRESH_TOKEN_EXPIRE_DAYS=30

# Firebase
FIREBASE_PROJECT_ID=...
FIREBASE_PRIVATE_KEY=...
FIREBASE_CLIENT_EMAIL=...

# Cookies (opcional)
COOKIE_DOMAIN=.cisnaturatienda.com  # Solo producción

# CORS (importante para cookies)
CORS_ALLOW_ORIGINS=https://cisnaturatienda.com
```

## Migraciones y Compatibilidad

### Estado Actual (Híbrido)

El sistema actualmente soporta:
1. ✅ Cookies HttpOnly (nuevo, más seguro)
2. ✅ Bearer tokens en header (compatibilidad)
3. ✅ Cookies NO HttpOnly (temporal, para migración)

### Migración Futura

Para migrar completamente a HttpOnly:

1. **Frontend**: Dejar de leer `access_token` de cookies
2. **Frontend**: Usar solo `withCredentials: true`
3. **Backend**: Remover tokens del body de respuesta (opcional)
4. **Backend**: Habilitar CSRF middleware

```python
# En main.py, descomentar:
from core.csrf_protection import CSRFMiddleware
app.add_middleware(CSRFMiddleware)
```

## Checklist de Seguridad

- [x] Tokens almacenados en cookies HttpOnly
- [x] Cookies con `Secure=true` en producción
- [x] Cookies con `SameSite=Lax`
- [x] Firebase token validado en backend
- [x] JWT emitido por backend después de validar Firebase
- [x] Token blacklist en Redis para logout
- [x] CSRF token generado para formularios
- [ ] CSRF middleware habilitado (opcional)
- [x] CORS configurado para permitir credentials
- [x] Soporte dual (cookies + Bearer) para compatibilidad
