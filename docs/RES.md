# Guía de Respuestas de la API Cisnatura

## 📋 Estructura Estándar de Respuestas

Todas las respuestas de la API siguen un formato consistente para facilitar el manejo en el frontend.

### ✅ Respuesta Exitosa

```json
{
  "success": true,
  "status_code": 200,
  "message": "Descripción de la operación exitosa",
  "data": {
    // Datos de la respuesta
  }
}
```

### ❌ Respuesta de Error

```json
{
  "success": false,
  "status_code": 404,
  "message": "Descripción del error",
  "error": "CODIGO_ERROR"
}
```

## 🎯 Campos de la Respuesta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `success` | boolean | `true` si la operación fue exitosa, `false` si hubo error |
| `status_code` | number | Código HTTP de estado (200, 404, 500, etc.) |
| `message` | string | Mensaje descriptivo para mostrar al usuario |
| `data` | object | Datos de la respuesta (solo en éxito) |
| `error` | string | Código de error específico (solo en errores) |

## 📊 Códigos de Estado HTTP

| Código | Nombre | Uso |
|--------|--------|-----|
| 200 | OK | Operación exitosa (GET, PUT, DELETE) |
| 201 | Created | Recurso creado exitosamente (POST) |
| 400 | Bad Request | Error en la petición (datos inválidos) |
| 401 | Unauthorized | Usuario no autenticado |
| 403 | Forbidden | Usuario sin permisos |
| 404 | Not Found | Recurso no encontrado |
| 422 | Unprocessable Entity | Error de validación |
| 500 | Internal Server Error | Error del servidor |

## 📝 Ejemplos por Endpoint

### GET /products/
**Éxito (200)**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Productos obtenidos exitosamente",
  "data": {
    "products": [
      {
        "id": 1,
        "name": "Aceite Esencial de Lavanda",
        "slug": "aceite-lavanda",
        "description": "Aceite 100% puro",
        "price": 299.99,
        "stock": 50,
        "category_id": 1,
        "image_url": "https://...",
        "created_at": "2025-11-13T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 45,
      "total_pages": 5,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### GET /products/{id}
**Éxito (200)**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Producto obtenido exitosamente",
  "data": {
    "id": 1,
    "name": "Aceite Esencial de Lavanda",
    "slug": "aceite-lavanda",
    "description": "Aceite 100% puro",
    "price": 299.99,
    "stock": 50,
    "category_id": 1,
    "image_url": "https://...",
    "created_at": "2025-11-13T10:00:00Z",
    "updated_at": "2025-11-13T12:00:00Z"
  }
}
```

**Error (404)**
```json
{
  "success": false,
  "status_code": 404,
  "message": "Producto no encontrado",
  "error": "PRODUCT_NOT_FOUND"
}
```

### POST /products/ (Crear)
**Éxito (201)**
```json
{
  "success": true,
  "status_code": 201,
  "message": "Producto creado exitosamente",
  "data": {
    "id": 10,
    "name": "Nuevo Producto",
    "slug": "nuevo-producto"
  }
}
```

**Error (400)**
```json
{
  "success": false,
  "status_code": 400,
  "message": "El slug ya existe",
  "error": "DUPLICATE_SLUG"
}
```

### PUT /products/{id} (Actualizar)
**Éxito (200)**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Producto actualizado exitosamente",
  "data": {
    "id": 1,
    "name": "Producto Actualizado"
  }
}
```

### DELETE /products/{id} (Eliminar)
**Éxito (200)**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Producto eliminado exitosamente",
  "data": {
    "id": 1,
    "name": "Producto",
    "is_active": false
  }
}
```

## 🔐 Errores de Autenticación

### 401 - No autenticado
```json
{
  "success": false,
  "status_code": 401,
  "message": "Autenticación requerida",
  "error": "UNAUTHORIZED"
}
```

### 403 - Sin permisos
```json
{
  "success": false,
  "status_code": 403,
  "message": "No tienes permisos para realizar esta acción",
  "error": "FORBIDDEN"
}
```

## 💻 Manejo en Frontend (JavaScript)

```javascript
// GET - Obtener productos
const response = await fetch('/products/?page=1');
const json = await response.json();

if (json.success) {
  console.log(json.data.products);
} else {
  console.error(json.message);
}

// POST - Crear producto (requiere auth)
const response = await fetch('/products/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    name: "Nuevo Producto",
    slug: "nuevo-producto",
    price: 299.99,
    stock: 10,
    category_id: 1
  })
});

// PUT - Actualizar producto
const response = await fetch('/products/1', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    price: 349.99,
    stock: 25
  })
});

// DELETE - Eliminar producto
const response = await fetch('/products/1', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## 📌 Códigos de Error Específicos

| Código | Descripción |
|--------|-------------|
| `PRODUCT_NOT_FOUND` | Producto no existe |
| `CATEGORY_NOT_FOUND` | Categoría no existe |
| `UNAUTHORIZED` | Usuario no autenticado |
| `FORBIDDEN` | Sin permisos suficientes |
| `VALIDATION_ERROR` | Error en validación de datos |
| `DUPLICATE_SLUG` | El slug ya existe |
| `INSUFFICIENT_STOCK` | Stock insuficiente |

## ✨ Buenas Prácticas

1. **Siempre verificar `success`** antes de acceder a `data`
2. **Usar `status_code`** para lógica específica de HTTP
3. **Mostrar `message`** al usuario cuando sea apropiado
4. **Verificar `error`** para casos especiales
5. **Incluir token** en headers para endpoints de admin
