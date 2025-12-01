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

### Endpoints Admin (Requieren Autenticación)

**Base URL:** `/admin/settings`

Todos estos endpoints requieren token de administrador.

---

## 📖 Endpoints GET - Obtener Configuraciones

### 1. Obtener TODAS las Configuraciones

```http
GET /admin/settings
Authorization: Bearer {admin_token}
```

**Respuesta:** Devuelve el objeto completo con todas las configuraciones.

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

---

### 2. Obtener Configuración de Mantenimiento

```http
GET /admin/settings/maintenance
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Configuración de mantenimiento obtenida exitosamente",
  "data": {
    "maintenance_mode": false,
    "maintenance_message": "Sistema en mantenimiento..."
  }
}
```

---

### 3. Obtener Configuración de Envío

```http
GET /admin/settings/shipping
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Configuración de envío obtenida exitosamente",
  "data": {
    "shipping_price": 250.0,
    "free_shipping_threshold": 2000.0
  }
}
```

---

### 4. Obtener TODOS los Descuentos (Panel Principal)

```http
GET /admin/settings/discounts
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuentos obtenidos exitosamente",
  "data": {
    "global_discount": {
      "enabled": false,
      "percentage": 10.0,
      "name": "Oferta Especial"
    },
    "category_discounts": {
      "1": {
        "percentage": 15,
        "name": "Oferta Categoría 1"
      },
      "2": {
        "percentage": 20,
        "name": "Liquidación Categoría 2"
      }
    },
    "product_discounts": {
      "5": {
        "percentage": 25,
        "name": "Super Oferta"
      }
    }
  }
}
```

**Uso:** Ideal para mostrar todos los descuentos activos en un solo panel.

---

### 5. Obtener Solo Descuento Global

```http
GET /admin/settings/discount/global
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuento global obtenido exitosamente",
  "data": {
    "enabled": false,
    "percentage": 10.0,
    "name": "Oferta Especial"
  }
}
```

---

### 6. Obtener Descuentos por Categoría

```http
GET /admin/settings/discount/categories
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuentos por categoría obtenidos exitosamente",
  "data": {
    "category_discounts": {
      "1": {
        "percentage": 15,
        "name": "Oferta Categoría 1"
      },
      "2": {
        "percentage": 20,
        "name": "Liquidación Categoría 2"
      }
    }
  }
}
```

**Uso:** Para el panel específico de descuentos por categoría.

---

### 7. Obtener Descuentos por Producto

```http
GET /admin/settings/discount/products
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuentos por producto obtenidos exitosamente",
  "data": {
    "product_discounts": {
      "5": {
        "percentage": 25,
        "name": "Super Oferta"
      },
      "12": {
        "percentage": 30,
        "name": "Liquidación"
      }
    }
  }
}
```

**Uso:** Para el panel específico de descuentos por producto.

---

### 8. Obtener Ofertas Temporales

```http
GET /admin/settings/seasonal-offers
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Ofertas temporales obtenidas exitosamente",
  "data": {
    "seasonal_offers": [
      {
        "name": "Black Friday",
        "start_date": "2024-11-25",
        "end_date": "2024-11-30",
        "discount_percentage": 30,
        "category_ids": null,
        "product_ids": ["1", "2", "3"]
      }
    ]
  }
}
```

---

### 9. Obtener Configuración de Registro

```http
GET /admin/settings/registration
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Configuración de registro obtenida exitosamente",
  "data": {
    "allow_user_registration": true,
    "max_items_per_order": 50
  }
}
```

---

## ✏️ Endpoints PUT/POST/DELETE - Actualizar Configuraciones

### 10. Actualizar Modo Mantenimiento

```http
PUT /admin/settings/maintenance
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "maintenance_mode": true,
  "maintenance_message": "Estaremos de vuelta en 30 minutos"
}
```

```http
PUT /admin/settings/maintenance
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "maintenance_mode": true,
  "maintenance_message": "Estaremos de vuelta en 30 minutos"
}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Modo mantenimiento actualizado exitosamente",
  "data": {
    "maintenance_mode": true,
    "maintenance_message": "Estaremos de vuelta en 30 minutos"
  }
}
```

---

### 11. Actualizar Precio de Envío

```http
PUT /admin/settings/shipping
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "shipping_price": 250.0,
  "free_shipping_threshold": 2000.0
}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Precio de envío actualizado exitosamente",
  "data": {
    "shipping_price": 250.0,
    "free_shipping_threshold": 2000.0
  }
}
```

---

### 12. Actualizar Descuento Global

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

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuento global actualizado exitosamente",
  "data": {
    "enabled": true,
    "percentage": 10,
    "name": "Descuento de Verano"
  }
}
```

---

### 13. Agregar Descuento por Categoría

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

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuento agregado a categoría 5",
  "data": {
    "category_discounts": {
      "5": {
        "percentage": 15,
        "name": "Especial Cosmética"
      }
    }
  }
}
```

---

### 14. Eliminar Descuento por Categoría

```http
DELETE /admin/settings/discount/category/5
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuento eliminado de categoría 5",
  "data": {
    "category_discounts": {}
  }
}
```

---

### 15. Agregar Descuento por Producto

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

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuento agregado a producto 123",
  "data": {
    "product_discounts": {
      "123": {
        "percentage": 20,
        "name": "Liquidación"
      }
    }
  }
}
```

---

### 16. Eliminar Descuento por Producto

```http
DELETE /admin/settings/discount/product/123
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Descuento eliminado del producto 123",
  "data": {
    "product_discounts": {}
  }
}
```

---

### 17. Crear Oferta Temporal

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

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Oferta temporal 'Black Friday 2025' creada exitosamente",
  "data": {
    "seasonal_offers": [
      {
        "name": "Black Friday 2025",
        "start_date": "2025-11-24",
        "end_date": "2025-11-30",
        "discount_percentage": 30,
        "category_ids": ["1", "2", "5"],
        "product_ids": null
      }
    ]
  }
}
```

---

### 18. Eliminar Oferta Temporal

```http
DELETE /admin/settings/seasonal-offer/Black Friday 2025
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Oferta temporal 'Black Friday 2025' eliminada exitosamente",
  "data": {
    "seasonal_offers": []
  }
}
```

---

### 19. Actualizar Control de Registro

```http
PUT /admin/settings/user-registration
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "allow_user_registration": false
}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Configuración de registro actualizada exitosamente",
  "data": {
    "allow_user_registration": false
  }
}
```

---

### 20. Actualizar Límite de Items

```http
PUT /admin/settings/max-items
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "max_items_per_order": 100
}
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Límite de productos por orden actualizado exitosamente",
  "data": {
    "max_items_per_order": 100
  }
}
```

---

### 21. Resumen de Descuentos con Productos/Categorías

```http
GET /admin/settings/discounts/summary
Authorization: Bearer {admin_token}
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "global_discount": {
      "enabled": false,
      "percentage": null,
      "name": null
    },
    "categories": [
      {
        "id": 1,
        "name": "Cosmética",
        "has_discount": true,
        "discount": {
          "percentage": 20,
          "name": "Navidad"
        }
      },
      {
        "id": 2,
        "name": "Skincare",
        "has_discount": false,
        "discount": null
      }
    ],
    "products": [
      {
        "id": 5,
        "name": "Crema Hidratante",
        "category_id": 1,
        "has_discount": true,
        "discount": {
          "percentage": 25,
          "name": "Liquidación"
        }
      }
    ],
    "seasonal_offers": [],
    "summary": {
      "total_categories": 5,
      "categories_with_discount": 1,
      "total_products": 20,
      "products_with_discount": 3
    }
  }
}
```

**Uso:** Para poblar selectores en el dashboard del admin y mostrar qué productos/categorías tienen descuentos.

---

### Endpoints Públicos (Sin Autenticación)

**Base URL:** `/settings`

Estos endpoints están disponibles para todos los usuarios.

### 11. Configuraciones Públicas

```http
GET /settings/public
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "maintenance_mode": false,
    "maintenance_message": null,
    "allow_user_registration": true,
    "active_offers": [
      {
        "name": "Black Friday",
        "discount_percentage": 30,
        "end_date": "2025-11-30"
      }
    ],
    "has_global_discount": true,
    "global_discount_name": "Descuento de Verano"
  }
}
```

**Uso:** Mostrar mensajes de ofertas activas, banner de mantenimiento, etc.

### 12. Calcular Costo de Envío

```http
GET /settings/shipping/calculate?total=150.50
```

**Respuesta con envío normal:**
```json
{
  "success": true,
  "data": {
    "shipping_price": 5.99,
    "is_free": false,
    "threshold": 200.0,
    "remaining_for_free": 49.5
  }
}
```

**Respuesta con envío gratis:**
```json
{
  "success": true,
  "data": {
    "shipping_price": 0.0,
    "is_free": true,
    "threshold": 200.0,
    "message": "¡Envío gratis por compra mayor a $200!"
  }
}
```

**Uso:** En el carrito o checkout para calcular el envío antes de finalizar la orden.

### 13. Información de Envío

```http
GET /settings/shipping/info
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "shipping_price": 5.99,
    "free_shipping_threshold": 200.0,
    "message": "Envío $5.99 (gratis en compras mayores a $200)"
  }
}
```

**Uso:** Mostrar en la página principal o banner informativo.

---

## ⚠️ Restricciones de Descuentos

### Descuento Global Exclusivo

**Importante:** Si activas un descuento global, se eliminarán automáticamente todos los descuentos específicos (categorías, productos y ofertas temporales).

**Comportamiento:**
- ✅ **Descuento Global Activo** → No se pueden agregar descuentos de categoría ni producto
- ✅ **Descuentos Específicos** → El descuento global debe estar desactivado

**Ejemplo de error:**
```bash
POST /admin/settings/discount/category
{
  "category_id": "1",
  "percentage": 20,
  "name": "Navidad"
}

# Con descuento global activo:
Response 400:
{
  "success": false,
  "message": "No se pueden agregar descuentos por categoría mientras hay un descuento global activo. Desactiva el descuento global primero.",
  "error": "GLOBAL_DISCOUNT_ACTIVE"
}
```

**Flujo correcto:**
```bash
# 1. Desactivar descuento global
PUT /admin/settings/discount/global
{"enabled": false, "percentage": 0, "name": ""}

# 2. Ahora puedes agregar descuentos específicos
POST /admin/settings/discount/category
{"category_id": "1", "percentage": 20, "name": "Navidad"}
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

### Arquitectura de Paneles

Con los nuevos endpoints GET específicos, cada panel en tu dashboard puede cargar solo la información que necesita:

```
Dashboard Admin
├── Panel Mantenimiento      → GET /admin/settings/maintenance
├── Panel Envío              → GET /admin/settings/shipping
├── Panel Descuentos         
│   ├── Descuento Global     → GET /admin/settings/discount/global
│   ├── Por Categoría        → GET /admin/settings/discount/categories
│   └── Por Producto         → GET /admin/settings/discount/products
├── Panel Ofertas Temporales → GET /admin/settings/seasonal-offers
└── Panel Registro           → GET /admin/settings/registration
```

### Ejemplo: Panel de Descuentos

```jsx
// DiscountsPanel.jsx
import { useEffect, useState } from 'react';

const DiscountsPanel = () => {
  const [discounts, setDiscounts] = useState(null);
  const [loading, setLoading] = useState(true);

  // Cargar todos los descuentos para el panel
  useEffect(() => {
    fetch('/admin/settings/discounts', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        setDiscounts(data.data);
        setLoading(false);
      });
  }, []);

  const deleteProductDiscount = async (productId) => {
    await fetch(`/admin/settings/discount/product/${productId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    // Recargar descuentos
    const response = await fetch('/admin/settings/discount/products', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    setDiscounts({
      ...discounts,
      product_discounts: data.data.product_discounts
    });
  };

  const deleteCategoryDiscount = async (categoryId) => {
    await fetch(`/admin/settings/discount/category/${categoryId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    // Recargar descuentos
    const response = await fetch('/admin/settings/discount/categories', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    setDiscounts({
      ...discounts,
      category_discounts: data.data.category_discounts
    });
  };

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="discounts-panel">
      {/* Descuento Global */}
      <section>
        <h2>Descuento Global</h2>
        {discounts.global_discount.enabled ? (
          <div className="discount-card active">
            <h3>{discounts.global_discount.name}</h3>
            <p>{discounts.global_discount.percentage}% de descuento</p>
            <button onClick={() => updateGlobalDiscount(false, 0, '')}>
              Desactivar
            </button>
          </div>
        ) : (
          <button onClick={() => setShowGlobalForm(true)}>
            Activar Descuento Global
          </button>
        )}
      </section>

      {/* Descuentos por Categoría */}
      <section>
        <h2>Descuentos por Categoría</h2>
        {Object.keys(discounts.category_discounts).length === 0 ? (
          <p>No hay descuentos por categoría</p>
        ) : (
          <ul>
            {Object.entries(discounts.category_discounts).map(([catId, disc]) => (
              <li key={catId} className="discount-item">
                <div>
                  <strong>Categoría {catId}</strong>
                  <p>{disc.name} - {disc.percentage}%</p>
                </div>
                <button onClick={() => deleteCategoryDiscount(catId)}>
                  🗑️ Eliminar
                </button>
              </li>
            ))}
          </ul>
        )}
        <button onClick={() => setShowCategoryForm(true)}>
          + Agregar Descuento por Categoría
        </button>
      </section>

      {/* Descuentos por Producto */}
      <section>
        <h2>Descuentos por Producto</h2>
        {Object.keys(discounts.product_discounts).length === 0 ? (
          <p>No hay descuentos por producto</p>
        ) : (
          <ul>
            {Object.entries(discounts.product_discounts).map(([prodId, disc]) => (
              <li key={prodId} className="discount-item">
                <div>
                  <strong>Producto {prodId}</strong>
                  <p>{disc.name} - {disc.percentage}%</p>
                </div>
                <button onClick={() => deleteProductDiscount(prodId)}>
                  🗑️ Eliminar
                </button>
              </li>
            ))}
          </ul>
        )}
        <button onClick={() => setShowProductForm(true)}>
          + Agregar Descuento por Producto
        </button>
      </section>
    </div>
  );
};
```

### Ejemplo: Panel de Envío

```jsx
// ShippingPanel.jsx
const ShippingPanel = () => {
  const [settings, setSettings] = useState(null);

  useEffect(() => {
    // Solo carga información de envío
    fetch('/admin/settings/shipping', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setSettings(data.data));
  }, []);

  const handleUpdate = async (e) => {
    e.preventDefault();
    
    await fetch('/admin/settings/shipping', {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        shipping_price: parseFloat(e.target.price.value),
        free_shipping_threshold: parseFloat(e.target.threshold.value)
      })
    });
    
    // Recargar
    const response = await fetch('/admin/settings/shipping', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    setSettings(data.data);
  };

  return (
    <div className="shipping-panel">
      <h2>Configuración de Envío</h2>
      {settings && (
        <form onSubmit={handleUpdate}>
          <label>
            Precio de Envío:
            <input 
              type="number" 
              name="price" 
              defaultValue={settings.shipping_price} 
              step="0.01"
            />
          </label>
          
          <label>
            Envío Gratis desde:
            <input 
              type="number" 
              name="threshold" 
              defaultValue={settings.free_shipping_threshold} 
              step="0.01"
            />
          </label>
          
          <button type="submit">Actualizar</button>
        </form>
      )}
    </div>
  );
};
```

### Ejemplo: Panel de Mantenimiento

```jsx
// MaintenancePanel.jsx
const MaintenancePanel = () => {
  const [settings, setSettings] = useState(null);

  useEffect(() => {
    fetch('/admin/settings/maintenance', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setSettings(data.data));
  }, []);

  const toggleMaintenance = async () => {
    const response = await fetch('/admin/settings/maintenance', {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        maintenance_mode: !settings.maintenance_mode,
        maintenance_message: settings.maintenance_message || 'Sistema en mantenimiento'
      })
    });
    
    const data = await response.json();
    setSettings(data.data);
  };

  return (
    <div className="maintenance-panel">
      <h2>Modo Mantenimiento</h2>
      {settings && (
        <>
          <div className={`status ${settings.maintenance_mode ? 'active' : 'inactive'}`}>
            Estado: {settings.maintenance_mode ? '🔴 Activo' : '🟢 Inactivo'}
          </div>
          
          <button onClick={toggleMaintenance}>
            {settings.maintenance_mode ? 'Desactivar' : 'Activar'} Mantenimiento
          </button>
          
          {settings.maintenance_mode && (
            <p className="message">{settings.maintenance_message}</p>
          )}
        </>
      )}
    </div>
  );
};
```

---

### Dashboard del Admin (Completo)

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
