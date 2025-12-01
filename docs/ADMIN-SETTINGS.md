# Sistema de Configuraciones Administrativas

Sistema completo para que el administrador controle configuraciones globales del e-commerce desde su dashboard.

## 📋 Tabla de Contenidos

- [Características](#características)
- [Migración de Base de Datos](#migración-de-base-de-datos)
- [Endpoints de la API](#endpoints-de-la-api)
- [Configuraciones Disponibles](#configuraciones-disponibles)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Integración con Frontend](#integración-con-frontend)

---

## ✨ Características

### 1. **Modo Mantenimiento**
- Bloquea el acceso a la API para usuarios normales
- Los administradores siempre pueden acceder
- Mensaje personalizable

### 2. **Precio de Envío**
- Configurar precio de envío dinámicamente
- Establecer umbral para envío gratis
- Ejemplo: "Envío gratis en compras mayores a $50"

### 3. **Sistema de Descuentos**
Con prioridad jerárquica:
1. **Descuentos por producto específico** (mayor prioridad)
2. **Ofertas estacionales para productos**
3. **Ofertas estacionales para categorías**
4. **Descuentos por categoría**
5. **Descuento global** (menor prioridad)

### 4. **Ofertas Temporales/Estacionales**
- Black Friday, Navidad, etc.
- Fecha de inicio y fin
- Aplicar a categorías específicas o todas
- Aplicar a productos específicos

### 5. **Control de Registro**
- Activar/desactivar registro de nuevos usuarios

### 6. **Límite de Productos por Orden**
- Configurar máximo de items por orden

---

## 🗄️ Migración de Base de Datos

### Opción 1: Usar Alembic (Recomendado)

```bash
# En desarrollo (Docker)
docker exec cisnatura_app alembic upgrade head

# En producción
docker exec <nombre_contenedor> alembic upgrade head
```

### Opción 2: SQL Directo

```sql
-- La migración ya incluye valores iniciales por defecto
-- No necesitas ejecutar SQL adicional
```

Para revertir:
```bash
docker exec cisnatura_app alembic downgrade -1
```

---

## 🔌 Endpoints de la API

Todos los endpoints requieren autenticación de administrador.

### Base URL
```
/admin/settings
```

### 1. Obtener Configuraciones

```http
GET /admin/settings
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "id": "uuid",
  "maintenance_mode": false,
  "maintenance_message": "Sistema en mantenimiento...",
  "shipping_price": 5.99,
  "free_shipping_threshold": 50.0,
  "global_discount_enabled": false,
  "global_discount_percentage": 0,
  "global_discount_name": "Oferta Especial",
  "category_discounts": {},
  "product_discounts": {},
  "seasonal_offers": [],
  "allow_user_registration": true,
  "max_items_per_order": 50
}
```

### 2. Modo Mantenimiento

```http
PUT /admin/settings/maintenance
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "maintenance_mode": true,
  "maintenance_message": "Estaremos de vuelta en 30 minutos"
}
```

### 3. Precio de Envío

```http
PUT /admin/settings/shipping
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "shipping_price": 5.99,
  "free_shipping_threshold": 50.0
}
```

### 4. Descuento Global

```http
PUT /admin/settings/discount/global
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "enabled": true,
  "percentage": 10,
  "name": "Descuento de Verano"
}
```

### 5. Descuento por Categoría

**Agregar/Actualizar:**
```http
POST /admin/settings/discount/category
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "category_id": "5",
  "percentage": 15,
  "name": "Especial Cosmética"
}
```

**Eliminar:**
```http
DELETE /admin/settings/discount/category/5
Authorization: Bearer {admin_token}
```

### 6. Descuento por Producto

**Agregar/Actualizar:**
```http
POST /admin/settings/discount/product
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "product_id": "123",
  "percentage": 20,
  "name": "Liquidación"
}
```

**Eliminar:**
```http
DELETE /admin/settings/discount/product/123
Authorization: Bearer {admin_token}
```

### 7. Ofertas Temporales

**Crear:**
```http
POST /admin/settings/seasonal-offer
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Black Friday 2025",
  "start_date": "2025-11-24",
  "end_date": "2025-11-30",
  "discount_percentage": 30,
  "category_ids": ["1", "2", "5"],
  "product_ids": null
}
```

**Eliminar:**
```http
DELETE /admin/settings/seasonal-offer/Black Friday 2025
Authorization: Bearer {admin_token}
```

### 8. Control de Registro

```http
PUT /admin/settings/user-registration
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "allow_user_registration": false
}
```

### 9. Límite de Items

```http
PUT /admin/settings/max-items
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "max_items_per_order": 100
}
```

---

## 📊 Configuraciones Disponibles

### Maintenance Mode
- `maintenance_mode` (boolean): Activar/desactivar mantenimiento
- `maintenance_message` (string): Mensaje mostrado a usuarios

**Comportamiento:**
- Usuarios normales: reciben `503 Service Unavailable`
- Administradores: acceso total sin restricciones
- Rutas públicas (`/`, `/health`, `/docs`) siempre disponibles

### Shipping
- `shipping_price` (float): Precio de envío en tu moneda
- `free_shipping_threshold` (float|null): Umbral para envío gratis

**Ejemplo:**
```json
{
  "shipping_price": 5.99,
  "free_shipping_threshold": 50.0
}
```
→ "Envío $5.99 (gratis en compras >$50)"

### Global Discount
- `global_discount_enabled` (boolean): Activar descuento global
- `global_discount_percentage` (float): Porcentaje 0-100
- `global_discount_name` (string): Nombre de la oferta

**Aplica a:** Todos los productos si no tienen descuentos específicos

### Category Discounts
JSON object: `{"category_id": {"percentage": 15, "name": "Oferta"}}`

**Ejemplo:**
```json
{
  "5": {"percentage": 15, "name": "Especial Cosmética"},
  "8": {"percentage": 10, "name": "Descuento Skincare"}
}
```

### Product Discounts
JSON object: `{"product_id": {"percentage": 20, "name": "Liquidación"}}`

**Ejemplo:**
```json
{
  "123": {"percentage": 20, "name": "Liquidación"},
  "456": {"percentage": 35, "name": "Última Unidad"}
}
```

### Seasonal Offers
Array de ofertas temporales:

```json
[
  {
    "name": "Black Friday",
    "start_date": "2025-11-24",
    "end_date": "2025-11-30",
    "discount_percentage": 30,
    "category_ids": ["1", "2"],
    "product_ids": null
  }
]
```

**Campos:**
- `name`: Nombre de la oferta
- `start_date`: Inicio (YYYY-MM-DD)
- `end_date`: Fin (YYYY-MM-DD)
- `discount_percentage`: Porcentaje 0-100
- `category_ids`: IDs de categorías (null = todas)
- `product_ids`: IDs de productos específicos (null = ninguno)

### Other Settings
- `allow_user_registration` (boolean): Permitir nuevos registros
- `max_items_per_order` (integer): Límite de productos por orden

---

## 📝 Ejemplos de Uso

### Escenario 1: Black Friday

```bash
# 1. Crear oferta temporal
curl -X POST https://api.cisnaturatienda.com/admin/settings/seasonal-offer \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Black Friday 2025",
    "start_date": "2025-11-24",
    "end_date": "2025-11-30",
    "discount_percentage": 30,
    "category_ids": null,
    "product_ids": null
  }'
```

**Resultado:**
- 30% de descuento en TODOS los productos
- Solo activo del 24 al 30 de noviembre
- Se aplica automáticamente en GET /products

### Escenario 2: Descuento en Categoría Específica

```bash
# Descuento permanente en categoría "Cosmética Natural"
curl -X POST https://api.cisnaturatienda.com/admin/settings/discount/category \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "5",
    "percentage": 15,
    "name": "Promoción Cosmética"
  }'
```

### Escenario 3: Envío Gratis

```bash
# Envío $5.99, gratis en compras >$50
curl -X PUT https://api.cisnaturatienda.com/admin/settings/shipping \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_price": 5.99,
    "free_shipping_threshold": 50.0
  }'
```

### Escenario 4: Mantenimiento del Sistema

```bash
# Activar modo mantenimiento
curl -X PUT https://api.cisnaturatienda.com/admin/settings/maintenance \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "maintenance_mode": true,
    "maintenance_message": "Actualizando sistema. Volvemos en 1 hora"
  }'
```

---

## 🎨 Integración con Frontend

### Dashboard del Admin

Crear componente `AdminSettingsPage.jsx`:

```jsx
// Obtener configuraciones
const getSettings = async () => {
  const response = await fetch('/admin/settings', {
    headers: {
      'Authorization': `Bearer ${adminToken}`
    }
  });
  return response.json();
};

// Activar modo mantenimiento
const toggleMaintenance = async (enabled, message) => {
  await fetch('/admin/settings/maintenance', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      maintenance_mode: enabled,
      maintenance_message: message
    })
  });
};

// Actualizar precio de envío
const updateShipping = async (price, threshold) => {
  await fetch('/admin/settings/shipping', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      shipping_price: price,
      free_shipping_threshold: threshold
    })
  });
};
```

### Mostrar Descuentos en Productos

Los endpoints de productos ya incluyen descuentos automáticamente:

```jsx
// GET /products ya retorna precios con descuento
const ProductCard = ({ product }) => {
  return (
    <div>
      <h3>{product.name}</h3>
      
      {product.has_discount && (
        <div className="discount-badge">
          {product.discount.discount_name}
          - {product.discount.discount_percentage}% OFF
        </div>
      )}
      
      <div className="price">
        {product.has_discount && (
          <span className="original-price">
            ${product.original_price}
          </span>
        )}
        <span className="final-price">
          ${product.price}
        </span>
      </div>
      
      {product.has_discount && (
        <span className="savings">
          Ahorras: ${product.discount.savings}
        </span>
      )}
    </div>
  );
};
```

### Calcular Envío en Checkout

```jsx
const calculateShipping = async (orderTotal) => {
  const settings = await fetch('/admin/settings').then(r => r.json());
  
  if (settings.free_shipping_threshold && 
      orderTotal >= settings.free_shipping_threshold) {
    return {
      price: 0,
      isFree: true,
      message: '¡Envío gratis!'
    };
  }
  
  return {
    price: settings.shipping_price,
    isFree: false,
    remaining: settings.free_shipping_threshold - orderTotal
  };
};
```

---

## 🔐 Seguridad

### Autenticación Requerida
Todos los endpoints de `/admin/settings` requieren:
- Token JWT válido
- Usuario con `is_admin = true`

### Middleware de Maintenance
- Usuarios normales: bloqueados durante mantenimiento
- Admins: siempre acceso completo
- Rutas públicas: siempre disponibles

### Validaciones
- Porcentajes: 0-100
- Precios: >= 0
- Fechas: formato YYYY-MM-DD
- Límites: valores razonables

---

## 🧪 Testing

### Prueba Manual

```bash
# 1. Login como admin
TOKEN=$(curl -X POST https://api.cisnaturatienda.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@cisnatura.com","password":"admin123"}' \
  | jq -r '.data.access_token')

# 2. Obtener configuraciones
curl https://api.cisnaturatienda.com/admin/settings \
  -H "Authorization: Bearer $TOKEN"

# 3. Activar descuento global del 10%
curl -X PUT https://api.cisnaturatienda.com/admin/settings/discount/global \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled":true,"percentage":10,"name":"Descuento Especial"}'

# 4. Verificar descuentos en productos
curl https://api.cisnaturatienda.com/products | jq '.data.products[0]'
```

---

## 📚 Prioridad de Descuentos

El sistema aplica **UN SOLO descuento** por producto (el mejor):

```
1. Descuento específico del producto (20%)
   ↓ Si no existe
2. Oferta temporal para ese producto (25%)
   ↓ Si no existe
3. Oferta temporal para su categoría (30%)
   ↓ Si no existe
4. Descuento de su categoría (15%)
   ↓ Si no existe
5. Descuento global (10%)
```

**Ejemplo:**
- Producto ID 123
- Categoría: Cosmética (ID 5)
- Descuento global: 10%
- Descuento categoría Cosmética: 15%
- Descuento producto 123: 20%

→ **Se aplica: 20%** (el más específico y mayor)

---

## 🚀 Próximos Pasos

1. **Aplicar migración:**
   ```bash
   docker exec cisnatura_app alembic upgrade head
   ```

2. **Verificar tabla creada:**
   ```bash
   docker exec cisnatura_db psql -U user -d cisnatura -c "\d admin_settings"
   ```

3. **Probar endpoints** con Postman o cURL

4. **Integrar en dashboard** del admin

5. **Documentar** en tu README principal

---

## 🐛 Troubleshooting

### Error: "ADMIN_REQUIRED"
→ El usuario no tiene `is_admin = true`

### Error: "MAINTENANCE_MODE"
→ Sistema en mantenimiento, solo admins pueden acceder

### Descuentos no se aplican
→ Verificar que los IDs de categoría/producto sean strings en JSON

### Migración falla
→ Verificar conexión a base de datos en DATABASE_URL

---

## 📞 Soporte

Si tienes dudas sobre la implementación, revisa:
- Documentación de Alembic: https://alembic.sqlalchemy.org
- Documentación de FastAPI: https://fastapi.tiangolo.com
- Código fuente: `app/models/admin_settings.py`, `app/routes/admin_settings.py`
