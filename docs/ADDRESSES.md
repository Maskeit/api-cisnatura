# Gestión de Direcciones de Entrega

## 📦 Características

- **Límite:** 3 direcciones por usuario
- **Dirección predeterminada:** Automática en la primera dirección
- **Operaciones:** Crear, leer, actualizar, eliminar
- **Protección:** Solo el usuario puede ver y gestionar sus direcciones

---

## 📡 Endpoints de Direcciones

### 1. **GET /addresses** - Listar direcciones del usuario

```bash
curl -X GET "http://localhost:8000/addresses" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Direcciones obtenidas exitosamente",
  "data": {
    "addresses": [
      {
        "id": 1,
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "full_name": "Juan Pérez",
        "phone": "5512345678",
        "rfc": "PERJ850101ABC",
        "label": "Casa",
        "street": "Av. Principal 123",
        "city": "Ciudad de México",
        "state": "CDMX",
        "postal_code": "01000",
        "country": "México",
        "is_default": true,
        "created_at": "2025-11-18T10:30:00Z"
      },
      {
        "id": 2,
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "full_name": "María González",
        "phone": "8181234567",
        "rfc": null,
        "label": "Oficina",
        "street": "Calle Secundaria 456",
        "city": "Monterrey",
        "state": "Nuevo León",
        "postal_code": "64000",
        "country": "México",
        "is_default": false,
        "created_at": "2025-11-17T15:20:00Z"
      }
    ],
    "total": 2,
    "max_addresses": 3
  }
}
```

**Características:**
- Ordenadas por `is_default` (predeterminada primero) y luego por fecha de creación
- Muestra el total de direcciones y el límite máximo

---

### 2. **GET /addresses/{address_id}** - Obtener dirección específica

```bash
curl -X GET "http://localhost:8000/addresses/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Dirección obtenida exitosamente",
  "data": {
    "id": 1,
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "full_name": "Juan Pérez",
    "phone": "5512345678",
    "rfc": "PERJ850101ABC",
    "label": "Casa",
    "street": "Av. Principal 123",
    "city": "Ciudad de México",
    "state": "CDMX",
    "postal_code": "01000",
    "country": "México",
    "is_default": true,
    "created_at": "2025-11-18T10:30:00Z"
  }
}
```

**Errores:**
- `404 ADDRESS_NOT_FOUND`: La dirección no existe o no pertenece al usuario

---

### 3. **POST /addresses** - Crear nueva dirección

```bash
curl -X POST "http://localhost:8000/addresses" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Juan Pérez",
    "phone": "5512345678",
    "rfc": "PERJ850101ABC",
    "label": "Casa",
    "street": "Av. Principal 123",
    "city": "Ciudad de México",
    "state": "CDMX",
    "postal_code": "01000",
    "country": "México",
    "is_default": false
  }'
```

**Campos:**
- `full_name` (requerido): Nombre completo del destinatario (2-255 caracteres)
- `phone` (requerido): Teléfono celular (10-20 dígitos, se limpian espacios y guiones automáticamente)
- `rfc` (opcional): RFC mexicano (12-13 caracteres, se convierte a mayúsculas automáticamente)
- `label` (opcional): Etiqueta descriptiva (Casa, Oficina, etc.)
- `street` (requerido): Calle y número (5-255 caracteres)
- `city` (requerido): Ciudad (2-120 caracteres)
- `state` (requerido): Estado o provincia (2-120 caracteres)
- `postal_code` (requerido): Código postal (3-10 caracteres alfanuméricos)
- `country` (requerido): País (2-80 caracteres)
- `is_default` (opcional): Si es la dirección predeterminada (default: false)

**Validaciones:**
- ✅ Teléfono: Solo números, mínimo 10 dígitos (se limpian espacios, guiones, paréntesis y +)
- ✅ RFC: Formato mexicano 12-13 caracteres (4 letras iniciales + alfanuméricos), se convierte a mayúsculas
- ✅ Código postal: Solo letras y números (se eliminan espacios y guiones)
- ✅ Límite de 3 direcciones por usuario
- ✅ Primera dirección se marca automáticamente como predeterminada
- ✅ Si se marca `is_default: true`, se actualiza la anterior

**Ejemplos de validación:**
```json
// Teléfono: cualquiera de estos formatos es válido
"phone": "55 1234 5678"  → se guarda como "5512345678"
"phone": "(55) 1234-5678" → se guarda como "5512345678"
"phone": "+52 55 1234 5678" → se guarda como "525512345678"

// RFC: se convierte automáticamente a mayúsculas
"rfc": "perj850101abc" → se guarda como "PERJ850101ABC"
"rfc": null → válido (opcional)
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "status_code": 201,
  "message": "Dirección creada exitosamente",
  "data": {
    "id": 3,
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "full_name": "Juan Pérez",
    "phone": "5512345678",
    "rfc": "PERJ850101ABC",
    "label": "Casa",
    "street": "Av. Principal 123",
    "city": "Ciudad de México",
    "state": "CDMX",
    "postal_code": "01000",
    "country": "México",
    "is_default": false,
    "created_at": "2025-11-18T11:00:00Z"
  }
}
```

**Errores:**
- `400 MAX_ADDRESSES_REACHED`: Ya tiene 3 direcciones registradas

---

### 4. **PUT /addresses/{address_id}** - Actualizar dirección

```bash
curl -X PUT "http://localhost:8000/addresses/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Juan Carlos Pérez",
    "phone": "5598765432",
    "rfc": "PECJ900215XYZ",
    "label": "Casa Principal",
    "postal_code": "01010"
  }'
```

**Características:**
- Todos los campos son opcionales (actualización parcial)
- Solo actualiza los campos proporcionados
- Si se marca `is_default: true`, se actualiza la dirección predeterminada anterior
- Permite cambiar el nombre, teléfono o RFC del destinatario para esa dirección específica

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Dirección actualizada exitosamente",
  "data": {
    "id": 1,
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "full_name": "Juan Carlos Pérez",
    "phone": "5598765432",
    "rfc": "PECJ900215XYZ",
    "label": "Casa Principal",
    "street": "Av. Principal 123",
    "city": "Ciudad de México",
    "state": "CDMX",
    "postal_code": "01010",
    "country": "México",
    "is_default": true,
    "created_at": "2025-11-18T10:30:00Z"
  }
}
```

**Errores:**
- `404 ADDRESS_NOT_FOUND`: La dirección no existe o no pertenece al usuario

---

### 5. **DELETE /addresses/{address_id}** - Eliminar dirección

```bash
curl -X DELETE "http://localhost:8000/addresses/2" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Características:**
- Si se elimina la dirección predeterminada, se marca automáticamente otra como predeterminada
- Solo se pueden eliminar direcciones propias

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Dirección eliminada exitosamente",
  "data": null
}
```

**Errores:**
- `404 ADDRESS_NOT_FOUND`: La dirección no existe o no pertenece al usuario

---

### 6. **PATCH /addresses/{address_id}/set-default** - Marcar como predeterminada

```bash
curl -X PATCH "http://localhost:8000/addresses/2/set-default" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Características:**
- Endpoint dedicado para cambiar la dirección predeterminada
- Actualiza automáticamente la dirección predeterminada anterior
- Más semántico que usar PUT con `is_default: true`

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Dirección marcada como predeterminada",
  "data": {
    "id": 2,
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "full_name": "María González",
    "phone": "8181234567",
    "rfc": null,
    "label": "Oficina",
    "street": "Calle Secundaria 456",
    "city": "Monterrey",
    "state": "Nuevo León",
    "postal_code": "64000",
    "country": "México",
    "is_default": true,
    "created_at": "2025-11-17T15:20:00Z"
  }
}
```

**Errores:**
- `404 ADDRESS_NOT_FOUND`: La dirección no existe o no pertenece al usuario

---

## 🔒 Seguridad

- **Autenticación requerida:** Todos los endpoints requieren JWT token
- **Aislamiento de datos:** Los usuarios solo pueden ver y gestionar sus propias direcciones
- **Validación de propiedad:** Se verifica `user_id` en todas las operaciones

---

## 📝 Casos de Uso

### Flujo típico de usuario:

1. **Primera dirección (automática como predeterminada):**
```bash
POST /addresses
{
  "full_name": "Juan Pérez",
  "phone": "55 1234 5678",
  "rfc": "PERJ850101ABC",
  "label": "Casa",
  "street": "Av. Principal 123",
  "city": "CDMX",
  "state": "CDMX",
  "postal_code": "01000",
  "country": "México"
}
# is_default se establece automáticamente en true
```

2. **Agregar dirección de trabajo (con nombre diferente, sin RFC):**
```bash
POST /addresses
{
  "full_name": "María González",
  "phone": "(81) 8123-4567",
  "label": "Oficina",
  "street": "Calle Trabajo 456",
  "city": "CDMX",
  "state": "CDMX",
  "postal_code": "02000",
  "country": "México",
  "is_default": false
}
```

3. **Cambiar dirección predeterminada:**
```bash
PATCH /addresses/2/set-default
# Ahora la oficina es la predeterminada
```

4. **Actualizar teléfono y RFC:**
```bash
PUT /addresses/1
{
  "phone": "+52 55 9876 5432",
  "rfc": "PECJ900215XYZ"
}
```

5. **Actualizar código postal:**
```bash
PUT /addresses/1
{
  "postal_code": "01010"
}
```

6. **Eliminar dirección antigua:**
```bash
DELETE /addresses/1
```

---

## 💡 Casos de Uso Especiales

### Nombres y Teléfonos Diferentes

Los campos `full_name`, `phone` y `rfc` permiten flexibilidad para:

- **Envíos a familiares:** Dirección con nombre y teléfono de otra persona
- **Envíos corporativos:** RFC de empresa para facturación
- **Regalos:** Datos del destinatario final
- **Facturación:** RFC para personas físicas o morales

**Ejemplo:**
```json
// Usuario registrado: "Juan Pérez" (55-1111-2222)
// Direcciones con diferentes destinatarios:

{
  "full_name": "Juan Pérez",
  "phone": "5511112222",
  "rfc": "PERJ850101ABC",      // RFC personal
  "label": "Casa"
}
{
  "full_name": "María González",
  "phone": "5599998888",          // Teléfono de mamá
  "rfc": null,                    // Sin RFC
  "label": "Casa de Mamá"
}
{
  "full_name": "Tech Solutions SA de CV",
  "phone": "5555551234",
  "rfc": "TSO1501019Z3",          // RFC moral
  "label": "Oficina"
}
```

### Validación de RFC

El sistema valida automáticamente:
- **Longitud:** 12 caracteres (personas físicas) o 13 (personas morales)
- **Formato:** 4 letras iniciales + números/letras
- **Conversión:** Se convierte automáticamente a mayúsculas

```bash
# Ejemplos válidos de RFC:
"PERJ850101ABC"  # Persona física (12 caracteres)
"TSO1501019Z3"   # Persona moral (13 caracteres)
"perj850101abc"  # Se convierte a: PERJ850101ABC

# RFC opcional (puede ser null):
"rfc": null      # Válido para direcciones sin facturación
```

---

## 🧪 Pruebas con curl

### Obtener token de autenticación
```bash
# 1. Registrar usuario
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@ejemplo.com",
    "password": "Test123456",
    "full_name": "Usuario Test"
  }'

# 2. Verificar email (obtener token del email o base de datos)
curl -X POST "http://localhost:8000/auth/verify-email" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TOKEN_FROM_EMAIL"
  }'

# 3. Hacer login
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@ejemplo.com&password=Test123456" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")

echo $TOKEN
```

### Crear y gestionar direcciones
```bash
# Crear primera dirección (con RFC)
curl -X POST "http://localhost:8000/addresses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Juan Pérez",
    "phone": "5512345678",
    "rfc": "PERJ850101ABC",
    "label": "Casa",
    "street": "Av. Principal 123",
    "city": "Ciudad de México",
    "state": "CDMX",
    "postal_code": "01000",
    "country": "México"
  }'

# Crear dirección sin RFC
curl -X POST "http://localhost:8000/addresses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "María González",
    "phone": "(81) 8123-4567",
    "label": "Oficina",
    "street": "Calle Trabajo 456",
    "city": "Monterrey",
    "state": "Nuevo León",
    "postal_code": "64000",
    "country": "México"
  }'

# Listar direcciones
curl -X GET "http://localhost:8000/addresses" \
  -H "Authorization: Bearer $TOKEN"

# Actualizar teléfono y RFC
curl -X PUT "http://localhost:8000/addresses/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+52 55 9876 5432",
    "rfc": "PECJ900215XYZ",
    "label": "Casa Principal"
  }'
```

---

## 🗄️ Modelo de Base de Datos

```sql
CREATE TABLE addresses (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    rfc VARCHAR(13),
    label VARCHAR(80),
    street VARCHAR(255) NOT NULL,
    city VARCHAR(120) NOT NULL,
    state VARCHAR(120) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    country VARCHAR(80) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_addresses_user_id ON addresses(user_id);
```

**Campos importantes:**
- `full_name`: Nombre del destinatario (puede ser diferente al usuario)
- `phone`: Teléfono de contacto para el envío (obligatorio)
- `rfc`: RFC para facturación (opcional, 12-13 caracteres)
- `label`: Etiqueta descriptiva opcional

**Usos:**
- Generar guías de envío con nombre y teléfono correctos
- Facturación electrónica con RFC
- Envíos a terceros o familiares
- Direcciones corporativas con razón social y RFC moral

---

## 🚀 Integración con Pedidos (Futuro)

Cuando implementes el sistema de pedidos, las direcciones se usarán así:

```json
POST /orders
{
  "address_id": 1,
  "items": [...],
  "payment_method": "..."
}
```

La dirección quedará vinculada al pedido para mantener histórico, incluso si el usuario la elimina después.

**Para generar guías de envío, tendrás acceso a:**
- `full_name`: Nombre del destinatario (puede ser diferente al usuario registrado)
- `phone`: Teléfono de contacto (limpio, solo dígitos)
- `rfc`: RFC para facturación electrónica (opcional)
- `street`, `city`, `state`, `postal_code`, `country`: Datos completos de envío
- `label`: Referencia opcional (Casa, Oficina, etc.)

**Integración con APIs de paquetería:**
```json
// Datos listos para APIs como FedEx, DHL, Estafeta, etc.
{
  "recipient": {
    "name": "Juan Pérez",
    "phone": "5512345678",
    "tax_id": "PERJ850101ABC"  // RFC
  },
  "address": {
    "street": "Av. Principal 123",
    "city": "Ciudad de México",
    "state": "CDMX",
    "postal_code": "01000",
    "country": "México"
  }
}
```

---

## ✅ Resumen de Funcionalidades

| Funcionalidad | Implementado |
|---------------|--------------|
| Crear dirección | ✅ |
| Listar direcciones | ✅ |
| Ver dirección específica | ✅ |
| Actualizar dirección | ✅ |
| Eliminar dirección | ✅ |
| Marcar como predeterminada | ✅ |
| Límite de 3 direcciones | ✅ |
| Validación de código postal | ✅ |
| Auto-capitalización de etiquetas | ✅ |
| Protección por usuario | ✅ |
| Gestión automática de predeterminada | ✅ |

¡Sistema de direcciones completo y listo para usar! 🎉
