# 🔥 Implementación de Google Auth con Firebase - Backend

## ✅ Estado: Backend Implementado

### Archivos Modificados/Creados:

1. ✅ **`requirements.txt`** - Agregado `firebase-admin==6.5.0`
2. ✅ **`app/models/user.py`** - Agregados campos:
   - `firebase_uid` (UUID de Firebase)
   - `auth_provider` ("local" o "google")
   - `profile_image` (URL de foto de perfil)
   - `hashed_password` ahora nullable

3. ✅ **`app/schemas/auth.py`** - Agregados schemas:
   - `GoogleLoginRequest`
   - `GoogleAuthResponse`

4. ✅ **`app/core/firebase_service.py`** - Servicio completo de Firebase:
   - Inicialización con archivo o variables de entorno
   - Verificación de tokens
   - Manejo de errores

5. ✅ **`app/routes/auth.py`** - Endpoint `/auth/google-login`:
   - Verifica token de Firebase
   - Crea usuario si no existe
   - Vincula cuenta si existe
   - Retorna tokens JWT propios

6. ✅ **`app/main.py`** - Inicializa Firebase al arrancar
   - `redirect_slashes=False` para evitar 307

7. ✅ **`migration_google_auth.sql`** - Script de migración completo

---

## 📋 Pasos para Implementar

### 1. Instalar Dependencias

```bash
cd /Users/alejandre/Developer/cisnatura-ecommerce/api-cisnatura
pip install firebase-admin==6.5.0
```

### 2. Configurar Firebase Admin SDK

#### Opción A: Archivo serviceAccountKey.json (Desarrollo)

1. Ve a [Firebase Console](https://console.firebase.google.com/)
2. Selecciona tu proyecto
3. Settings (⚙️) → Project Settings
4. Service Accounts tab
5. Click "Generate New Private Key"
6. Guarda el archivo como `serviceAccountKey.json` en la raíz del proyecto
7. **IMPORTANTE:** Agrega a `.gitignore`:

```bash
echo "serviceAccountKey.json" >> .gitignore
```

8. Agrega a tu `.env`:

```env
FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json
```

#### Opción B: Variables de Entorno (Producción)

Agrega a tu `.env` (usa los valores del archivo descargado):

```env
FIREBASE_PROJECT_ID=tu-proyecto-id
FIREBASE_PRIVATE_KEY_ID=abc123...
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nTU_CLAVE_PRIVADA\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@tu-proyecto.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=123456789012345678901
FIREBASE_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
```

### 3. Ejecutar Migración de Base de Datos

```bash
# Desarrollo
docker exec -i cisnatura_db_dev psql -U user -d cisnatura < migration_google_auth.sql

# Producción
docker exec -i cisnatura_db psql -U user -d cisnatura < migration_google_auth.sql
```

Verificar que se aplicó correctamente:

```bash
docker exec -i cisnatura_db_dev psql -U user -d cisnatura -c "\d users"
```

Deberías ver los nuevos campos:
- `firebase_uid` (character varying 255)
- `auth_provider` (character varying 50, default 'local')
- `profile_image` (character varying 500)
- `hashed_password` ahora permite NULL

### 4. Reiniciar Aplicación

```bash
# Desarrollo
docker-compose down
docker-compose up -d

# O con make
make down
make up
```

### 5. Verificar que Firebase se Inicializó

Revisa los logs:

```bash
docker logs cisnatura_app_dev

# Deberías ver:
# ✅ Firebase inicializado desde archivo: ./serviceAccountKey.json
# o
# ✅ Firebase inicializado desde variables de entorno
```

---

## 🧪 Testing

### Prueba Manual con cURL

```bash
# Obtener un token de Firebase desde el frontend primero
# Luego probar el endpoint:

curl -X POST http://localhost:8000/auth/google-login \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "eyJhbGci...TU_TOKEN_DE_FIREBASE_AQUI"
  }'
```

Respuesta esperada:

```json
{
  "success": true,
  "status_code": 200,
  "message": "Login con Google exitoso",
  "data": {
    "access_token": "eyJhbGci...",
    "refresh_token": "eyJhbGci...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "uuid-here",
      "email": "user@gmail.com",
      "full_name": "Usuario Nombre",
      "is_active": true,
      "is_admin": false,
      "email_verified": true,
      "auth_provider": "google",
      "profile_image": "https://lh3.googleusercontent.com/..."
    },
    "is_new_user": true
  }
}
```

### Prueba desde el Frontend

1. Asegúrate que el frontend esté corriendo
2. Ve a `/login`
3. Click en "Continuar con Google"
4. Selecciona tu cuenta de Google
5. Deberías ser redirigido al dashboard

### Verificar en la Base de Datos

```sql
-- Ver usuarios de Google
SELECT 
    id,
    email,
    full_name,
    auth_provider,
    firebase_uid,
    email_verified,
    profile_image,
    created_at
FROM users
WHERE auth_provider = 'google';
```

---

## 🔒 Seguridad

### ✅ Implementado:

- Verificación de tokens con Firebase Admin SDK
- Tokens expirados son rechazados
- Tokens inválidos son rechazados
- Tokens revocados son rechazados
- Email verificado automáticamente por Google
- No se almacena contraseña para usuarios de Google
- Firebase UID único por usuario

### ⚠️ Recomendaciones Adicionales:

1. **Rate Limiting**: Agregar rate limit a `/auth/google-login`
2. **HTTPS en Producción**: Obligatorio
3. **CORS**: Ya configurado correctamente
4. **Logs**: Ya implementados con print(), considerar logger profesional
5. **Monitoring**: Monitorear intentos fallidos de autenticación

---

## 🐛 Troubleshooting

### Error: "Google Auth no configurado"

**Causa:** Firebase no se inicializó correctamente.

**Solución:**
1. Verificar que el archivo `serviceAccountKey.json` existe
2. O verificar que las variables de entorno están configuradas
3. Reiniciar la aplicación

### Error: "Token inválido"

**Causa:** El token de Firebase expiró o es inválido.

**Solución:**
- Los tokens de Firebase expiran en 1 hora
- El frontend debe obtener un nuevo token
- Verificar que el project ID coincide

### Error: "Usuario inactivo"

**Causa:** El usuario fue baneado/desactivado.

**Solución:**
- Activar el usuario desde el panel de admin
- Verificar con: `SELECT * FROM users WHERE email = 'user@example.com'`

### Error: Migración falla

**Causa:** La tabla ya tiene los campos o hay datos inconsistentes.

**Solución:**
```sql
-- Verificar qué campos ya existen
\d users

-- Si necesitas rehacer la migración, primero hacer rollback:
DROP INDEX IF EXISTS idx_users_firebase_uid;
DROP INDEX IF EXISTS idx_users_auth_provider;
ALTER TABLE users DROP COLUMN IF EXISTS firebase_uid;
ALTER TABLE users DROP COLUMN IF EXISTS auth_provider;
ALTER TABLE users DROP COLUMN IF EXISTS profile_image;

-- Luego volver a ejecutar el migration_google_auth.sql
```

---

## 📊 Métricas a Monitorear

- Total de usuarios por auth_provider
- Tasa de éxito de login con Google
- Tasa de error (token inválido, expirado, etc.)
- Usuarios nuevos vs existentes
- Tiempo de respuesta del endpoint

```sql
-- Query de métricas
SELECT 
    auth_provider,
    COUNT(*) as total_usuarios,
    COUNT(CASE WHEN email_verified = true THEN 1 END) as verificados,
    COUNT(CASE WHEN is_active = true THEN 1 END) as activos
FROM users
GROUP BY auth_provider;
```

---

## ✅ Checklist de Implementación

- [x] Instalar `firebase-admin`
- [x] Actualizar modelo `User`
- [x] Crear schemas de Google Auth
- [x] Crear servicio de Firebase
- [x] Crear endpoint `/auth/google-login`
- [x] Inicializar Firebase en `main.py`
- [x] Crear migración SQL
- [ ] Descargar `serviceAccountKey.json` de Firebase Console
- [ ] Agregar credenciales a `.env`
- [ ] Ejecutar migración en base de datos
- [ ] Reiniciar aplicación
- [ ] Probar login con Google desde frontend
- [ ] Verificar usuarios en base de datos
- [ ] Configurar rate limiting (opcional)
- [ ] Configurar monitoring (opcional)

---

## 🚀 Deployment a Producción

### Variables de Entorno

Agrega a tu `.env` de producción:

```env
# IMPORTANTE: Usar variables individuales, NO archivo JSON
FIREBASE_PROJECT_ID=tu-proyecto-real
FIREBASE_PRIVATE_KEY_ID=...
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=...
FIREBASE_CLIENT_ID=...
FIREBASE_CERT_URL=...
```

### Aplicar Migración

```bash
docker exec -i cisnatura_db psql -U user -d cisnatura < migration_google_auth.sql
```

### Reiniciar Servicios

```bash
docker-compose down
docker-compose up -d
```

### Verificar Logs

```bash
docker logs cisnatura_app | grep Firebase
```

---

## 📚 Documentación Adicional

- [Firebase Admin SDK Python](https://firebase.google.com/docs/admin/setup)
- [Verify ID Tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

**Última actualización:** 29 de noviembre de 2025
**Estado:** ✅ Backend Completado - Listo para Testing
