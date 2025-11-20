# 👤 API de Perfil de Usuario y Administración

Sistema completo de gestión de perfiles de usuario con endpoints para usuarios normales y administradores.

## 📋 Tabla de Contenidos

- [Endpoints de Usuario](#endpoints-de-usuario)
- [Endpoints de Administración](#endpoints-de-administración)
- [Schemas](#schemas)
- [Casos de Uso](#casos-de-uso)
- [Seguridad](#seguridad)

---

## 🔐 Endpoints de Usuario

### 1. Obtener Mi Perfil

```http
GET /users/me
Authorization: Bearer {token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Perfil obtenido exitosamente",
  "data": {
    "id": "uuid-here",
    "email": "user@example.com",
    "full_name": "Juan Pérez",
    "is_active": true,
    "is_admin": false,
    "email_verified": true,
    "email_verified_at": "2025-01-15T10:30:00Z",
    "created_at": "2025-01-01T12:00:00Z"
  }
}
```

**cURL:**
```bash
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2. Obtener Resumen de Perfil con Estadísticas

```http
GET /users/me/summary
Authorization: Bearer {token}
```

Incluye estadísticas completas del usuario:
- Total de órdenes (completadas, pendientes)
- Total gastado
- Direcciones guardadas
- Última orden

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Resumen de perfil obtenido exitosamente",
  "data": {
    "profile": {
      "id": "uuid-here",
      "email": "user@example.com",
      "full_name": "Juan Pérez",
      "is_active": true,
      "is_admin": false,
      "email_verified": true,
      "email_verified_at": "2025-01-15T10:30:00Z",
      "created_at": "2025-01-01T12:00:00Z"
    },
    "total_orders": 12,
    "completed_orders": 10,
    "pending_orders": 2,
    "total_spent": 5420.50,
    "total_addresses": 3,
    "has_default_address": true,
    "last_order": {
      "id": 45,
      "status": "delivered",
      "total": 877.20,
      "created_at": "2025-11-10T14:30:00Z"
    }
  }
}
```

**cURL:**
```bash
curl -X GET "http://localhost:8000/users/me/summary" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 3. Actualizar Mi Perfil

```http
PUT /users/me
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "full_name": "Juan Carlos Pérez López"
}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Perfil actualizado exitosamente",
  "data": {
    "id": "uuid-here",
    "email": "user@example.com",
    "full_name": "Juan Carlos Pérez López",
    "is_active": true,
    "is_admin": false,
    "email_verified": true,
    "email_verified_at": "2025-01-15T10:30:00Z",
    "created_at": "2025-01-01T12:00:00Z"
  }
}
```

**cURL:**
```bash
curl -X PUT "http://localhost:8000/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Juan Carlos Pérez López"
  }'
```

---

### 4. Cambiar Contraseña

```http
POST /users/me/change-password
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!",
  "confirm_password": "NewPassword456!"
}
```

**Validaciones:**
- Contraseña actual correcta
- Nueva contraseña mínimo 8 caracteres
- Nueva contraseña diferente a la actual
- Confirmación coincide con nueva contraseña

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Contraseña actualizada exitosamente"
}
```

**cURL:**
```bash
curl -X POST "http://localhost:8000/users/me/change-password" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "OldPassword123!",
    "new_password": "NewPassword456!",
    "confirm_password": "NewPassword456!"
  }'
```

**Errores:**
```json
{
  "success": false,
  "status_code": 400,
  "message": "Contraseña actual incorrecta",
  "error": "INVALID_PASSWORD"
}
```

---

### 5. Eliminar Mi Cuenta (Soft Delete)

```http
DELETE /users/me
Authorization: Bearer {token}
```

Desactiva la cuenta en lugar de eliminarla permanentemente.

**Restricción:** No se puede eliminar si hay órdenes pendientes.

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Cuenta desactivada exitosamente"
}
```

**Error si hay órdenes pendientes:**
```json
{
  "success": false,
  "status_code": 400,
  "message": "No puedes eliminar tu cuenta con 2 órdenes pendientes",
  "error": "PENDING_ORDERS"
}
```

**cURL:**
```bash
curl -X DELETE "http://localhost:8000/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 👨‍💼 Endpoints de Administración

Requieren autenticación y rol de **administrador**.

### 6. Listar Todos los Usuarios

```http
GET /users/admin/users?page=1&limit=20
Authorization: Bearer {admin_token}
```

**Parámetros de Query:**
- `page` (int): Número de página (default: 1)
- `limit` (int): Usuarios por página (default: 20, max: 100)
- `search` (string): Buscar por email o nombre
- `is_active` (bool): Filtrar por estado activo
- `is_admin` (bool): Filtrar por rol admin
- `email_verified` (bool): Filtrar por email verificado
- `created_from` (datetime): Registros desde fecha
- `created_to` (datetime): Registros hasta fecha

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Usuarios obtenidos exitosamente",
  "data": {
    "users": [
      {
        "id": "uuid-1",
        "email": "user1@example.com",
        "full_name": "Juan Pérez",
        "is_active": true,
        "is_admin": false,
        "email_verified": true,
        "email_verified_at": "2025-01-15T10:30:00Z",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-11-10T14:30:00Z",
        "total_orders": 12,
        "total_spent": 5420.50,
        "total_addresses": 3
      },
      {
        "id": "uuid-2",
        "email": "user2@example.com",
        "full_name": "María García",
        "is_active": true,
        "is_admin": false,
        "email_verified": false,
        "email_verified_at": null,
        "created_at": "2025-02-15T09:20:00Z",
        "updated_at": null,
        "total_orders": 5,
        "total_spent": 1820.00,
        "total_addresses": 1
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 156,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

**cURL con filtros:**
```bash
# Buscar usuarios activos con órdenes
curl -X GET "http://localhost:8000/users/admin/users?page=1&limit=20&is_active=true&search=juan" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Usuarios no verificados
curl -X GET "http://localhost:8000/users/admin/users?email_verified=false" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Usuarios registrados este mes
curl -X GET "http://localhost:8000/users/admin/users?created_from=2025-11-01T00:00:00Z" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

### 7. Obtener Detalles de Usuario

```http
GET /users/admin/users/{user_id}
Authorization: Bearer {admin_token}
```

Incluye información completa y últimas 5 órdenes.

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Usuario obtenido exitosamente",
  "data": {
    "id": "uuid-here",
    "email": "user@example.com",
    "full_name": "Juan Pérez",
    "is_active": true,
    "is_admin": false,
    "email_verified": true,
    "email_verified_at": "2025-01-15T10:30:00Z",
    "created_at": "2025-01-01T12:00:00Z",
    "updated_at": "2025-11-10T14:30:00Z",
    "total_orders": 12,
    "total_spent": 5420.50,
    "total_addresses": 3,
    "recent_orders": [
      {
        "id": 45,
        "status": "delivered",
        "total": 877.20,
        "created_at": "2025-11-10T14:30:00Z"
      },
      {
        "id": 44,
        "status": "shipped",
        "total": 1200.00,
        "created_at": "2025-11-05T10:15:00Z"
      }
    ]
  }
}
```

**cURL:**
```bash
curl -X GET "http://localhost:8000/users/admin/users/uuid-here" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

### 8. Actualizar Usuario

```http
PATCH /users/admin/users/{user_id}
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Body:**
```json
{
  "full_name": "Juan Carlos Pérez",
  "is_active": true,
  "is_admin": false,
  "email_verified": true
}
```

**Validaciones:**
- No puedes quitarte tus propios permisos de admin
- Todos los campos son opcionales

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Usuario actualizado exitosamente",
  "data": {
    "id": "uuid-here",
    "email": "user@example.com",
    "full_name": "Juan Carlos Pérez",
    "is_active": true,
    "is_admin": false,
    "email_verified": true,
    "email_verified_at": "2025-11-19T10:30:00Z",
    "created_at": "2025-01-01T12:00:00Z",
    "updated_at": "2025-11-19T15:45:00Z",
    "total_orders": 12,
    "total_spent": 5420.50,
    "total_addresses": 3
  }
}
```

**cURL:**
```bash
# Verificar email de usuario
curl -X PATCH "http://localhost:8000/users/admin/users/uuid-here" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_verified": true}'

# Promover a admin
curl -X PATCH "http://localhost:8000/users/admin/users/uuid-here" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_admin": true}'
```

**Error al auto-quitarse permisos:**
```json
{
  "success": false,
  "status_code": 400,
  "message": "No puedes quitarte tus propios permisos de administrador",
  "error": "CANNOT_DEMOTE_SELF"
}
```

---

### 9. Banear Usuario

```http
POST /users/admin/users/{user_id}/ban
Authorization: Bearer {admin_token}
Content-Type: application/json
```

Desactiva la cuenta del usuario (soft delete).

**Body (opcional):**
```json
{
  "reason": "Violación de términos de servicio"
}
```

**Restricciones:**
- No puedes banear a otros admins
- No puedes banearte a ti mismo

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Usuario baneado exitosamente: Violación de términos de servicio",
  "data": {
    "user_id": "uuid-here",
    "email": "user@example.com",
    "is_active": false,
    "reason": "Violación de términos de servicio"
  }
}
```

**cURL:**
```bash
curl -X POST "http://localhost:8000/users/admin/users/uuid-here/ban" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Violación de términos de servicio"}'
```

**Errores:**
```json
{
  "success": false,
  "status_code": 400,
  "message": "No puedes banear a un administrador",
  "error": "CANNOT_BAN_ADMIN"
}
```

---

### 10. Desbanear Usuario

```http
POST /users/admin/users/{user_id}/unban
Authorization: Bearer {admin_token}
```

Reactiva la cuenta del usuario.

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Usuario desbaneado exitosamente",
  "data": {
    "user_id": "uuid-here",
    "email": "user@example.com",
    "is_active": true
  }
}
```

**cURL:**
```bash
curl -X POST "http://localhost:8000/users/admin/users/uuid-here/unban" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

### 11. Eliminar Usuario Permanentemente

```http
DELETE /users/admin/users/{user_id}
Authorization: Bearer {admin_token}
```

⚠️ **PRECAUCIÓN:** Acción IRREVERSIBLE. Elimina el usuario y todas sus relaciones.

**Restricciones:**
- No puedes eliminar admins
- No puedes eliminarte a ti mismo
- Se recomienda usar ban/unban en su lugar

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Usuario eliminado permanentemente"
}
```

**cURL:**
```bash
curl -X DELETE "http://localhost:8000/users/admin/users/uuid-here" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Errores:**
```json
{
  "success": false,
  "status_code": 400,
  "message": "No puedes eliminar a un administrador",
  "error": "CANNOT_DELETE_ADMIN"
}
```

---

### 12. Estadísticas de Usuarios

```http
GET /users/admin/stats
Authorization: Bearer {admin_token}
```

Retorna estadísticas generales del sistema de usuarios.

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Estadísticas obtenidas exitosamente",
  "data": {
    "total_users": 1524,
    "active_users": 1450,
    "inactive_users": 74,
    "admin_users": 5,
    "verified_users": 1380,
    "unverified_users": 144,
    "new_users_today": 12,
    "new_users_this_week": 87,
    "new_users_this_month": 342,
    "top_spenders": [
      {
        "user_id": "uuid-1",
        "email": "topbuyer@example.com",
        "full_name": "Carlos Mendoza",
        "total_orders": 45,
        "total_spent": 28540.80
      },
      {
        "user_id": "uuid-2",
        "email": "buyer2@example.com",
        "full_name": "Ana López",
        "total_orders": 38,
        "total_spent": 19320.50
      }
    ]
  }
}
```

**cURL:**
```bash
curl -X GET "http://localhost:8000/users/admin/stats" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## 📊 Schemas

### UserProfileResponse
```typescript
{
  id: string;           // UUID del usuario
  email: string;        // Email único
  full_name: string;    // Nombre completo
  is_active: boolean;   // Usuario activo
  is_admin: boolean;    // Es administrador
  email_verified: boolean;  // Email verificado
  email_verified_at: datetime | null;
  created_at: datetime;
}
```

### UserUpdateProfile
```typescript
{
  full_name?: string;   // Nombre completo (opcional)
}
```

### UserChangePassword
```typescript
{
  current_password: string;   // Contraseña actual (min 8 chars)
  new_password: string;       // Nueva contraseña (min 8 chars)
  confirm_password: string;   // Confirmación (debe coincidir)
}
```

### UserAdminUpdate
```typescript
{
  full_name?: string;          // Nombre completo
  is_active?: boolean;         // Activar/desactivar
  is_admin?: boolean;          // Otorgar/quitar admin
  email_verified?: boolean;    // Marcar como verificado
}
```

### UserBanRequest
```typescript
{
  reason?: string;   // Razón del baneo (max 500 chars)
}
```

---

## 🎯 Casos de Uso

### Usuario Normal

#### 1. Ver mi dashboard de perfil
```bash
# Obtener resumen completo con estadísticas
GET /users/me/summary
```

#### 2. Actualizar mi información
```bash
# Cambiar nombre
PUT /users/me
Body: {"full_name": "Nuevo Nombre"}

# Cambiar contraseña
POST /users/me/change-password
Body: {
  "current_password": "old",
  "new_password": "new",
  "confirm_password": "new"
}
```

#### 3. Cerrar mi cuenta
```bash
# Desactivar cuenta (reversible por admin)
DELETE /users/me
```

---

### Administrador

#### 1. Dashboard de usuarios
```bash
# Estadísticas generales
GET /users/admin/stats

# Ver top compradores
# (incluido en stats)
```

#### 2. Gestión de usuarios
```bash
# Buscar usuario específico
GET /users/admin/users?search=juan@example.com

# Ver detalles completos
GET /users/admin/users/{user_id}

# Actualizar información
PATCH /users/admin/users/{user_id}
Body: {"is_active": false}
```

#### 3. Moderación
```bash
# Banear usuario problemático
POST /users/admin/users/{user_id}/ban
Body: {"reason": "Spam"}

# Desbanear después de revisión
POST /users/admin/users/{user_id}/unban

# Eliminar permanentemente (casos extremos)
DELETE /users/admin/users/{user_id}
```

#### 4. Verificación manual de emails
```bash
# Si un usuario tiene problemas con verificación
PATCH /users/admin/users/{user_id}
Body: {"email_verified": true}
```

#### 5. Promoción a administrador
```bash
# Dar permisos de admin
PATCH /users/admin/users/{user_id}
Body: {"is_admin": true}
```

---

## 🔒 Seguridad

### Autenticación
Todos los endpoints requieren token JWT válido:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Roles

#### Usuario Normal (`is_admin: false`)
- ✅ Ver y editar su propio perfil
- ✅ Ver sus estadísticas
- ✅ Cambiar su contraseña
- ✅ Desactivar su cuenta
- ❌ Ver otros usuarios
- ❌ Modificar otros usuarios
- ❌ Acceder a estadísticas generales

#### Administrador (`is_admin: true`)
- ✅ Todo lo anterior
- ✅ Listar todos los usuarios
- ✅ Ver detalles de cualquier usuario
- ✅ Modificar cualquier usuario
- ✅ Banear/desbanear usuarios
- ✅ Eliminar usuarios
- ✅ Ver estadísticas del sistema
- ✅ Verificar emails manualmente
- ✅ Promover a administrador
- ❌ Quitarse sus propios permisos de admin
- ❌ Banear o eliminar otros admins

### Validaciones

#### Contraseña
- Mínimo 8 caracteres
- Nueva contraseña diferente a la actual
- Contraseña actual correcta para cambios

#### Nombre
- Mínimo 2 caracteres
- Máximo 255 caracteres

#### Eliminación de Cuenta
- No permitida si hay órdenes pendientes
- Soft delete por defecto (desactivación)
- Hard delete solo para admins

#### Baneos
- No se puede banear a administradores
- No se puede banear a uno mismo
- Razón opcional (max 500 caracteres)

---

## 📈 Integración con Frontend

### Dashboard de Usuario
```typescript
// Obtener datos del dashboard
const response = await fetch('/users/me/summary', {
  headers: { 'Authorization': `Bearer ${token}` }
});

const { data } = await response.json();

// Renderizar:
// - Profile info: data.profile
// - Orders summary: data.total_orders, data.completed_orders
// - Spending: data.total_spent
// - Last order: data.last_order
```

### Panel de Administración
```typescript
// Página de usuarios
const users = await fetch('/users/admin/users?page=1&limit=20', {
  headers: { 'Authorization': `Bearer ${adminToken}` }
});

// Dashboard admin
const stats = await fetch('/users/admin/stats', {
  headers: { 'Authorization': `Bearer ${adminToken}` }
});
```

---

## 🔄 Relaciones con Otras APIs

### Con Órdenes (`/orders`)
- Ver órdenes del usuario en perfil
- Calcular total gastado
- Verificar órdenes pendientes antes de eliminar

### Con Direcciones (`/addresses`)
- Contar direcciones guardadas
- Verificar dirección predeterminada

### Con Autenticación (`/auth`)
- Login/registro crea usuarios
- Cambio de contraseña actualiza credenciales
- Verificación de email actualiza `email_verified`

---

## 📝 Notas Importantes

1. **Soft Delete por Defecto**: Las eliminaciones de usuario son reversibles (desactivación)
2. **Hard Delete con Precaución**: Solo admins, y solo en casos extremos
3. **Protección de Admins**: Los admins no pueden banearse o eliminarse entre sí
4. **Órdenes Pendientes**: Bloquean la auto-eliminación de cuenta
5. **Estadísticas en Tiempo Real**: Calculadas dinámicamente en cada request
6. **Top Spenders**: Solo incluye órdenes con estado `delivered`
7. **Verificación Manual**: Admins pueden verificar emails sin necesidad del token

---

## 🚀 Próximas Mejoras

- [ ] Notificaciones por email al cambiar contraseña
- [ ] Registro de actividad (audit log)
- [ ] Exportar usuarios a CSV/Excel
- [ ] Análisis de comportamiento de usuarios
- [ ] Segmentación de usuarios por características
- [ ] Sistema de puntos/recompensas
- [ ] Preferencias de usuario (tema, notificaciones)
- [ ] Avatar de perfil con uploads
- [ ] Autenticación de dos factores (2FA)
- [ ] Razones de baneo predefinidas
