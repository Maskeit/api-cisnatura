# Sistema de Órdenes de Compra

## 📦 Características

- **Estados de orden:** 8 estados desde pending hasta delivered
- **Métodos de pago:** Stripe, PayPal, MercadoPago, OpenPay
- **Administración:** Panel completo para gestionar órdenes
- **Estadísticas:** Ganancias por período, productos más vendidos
- **Webhooks:** Preparado para integración con pasarelas de pago
- **Snapshot de productos:** Guarda precio y nombre al momento de la compra
- **Gestión de stock:** Reduce automáticamente el inventario

---

## 🔄 Estados de la Orden

| Estado | Descripción | Puede cambiar a |
|--------|-------------|-----------------|
| `pending` | Orden creada, esperando pago | `payment_pending`, `paid`, `cancelled` |
| `payment_pending` | Pago en proceso | `paid`, `cancelled` |
| `paid` | Pagada, esperando procesamiento | `processing`, `refunded` |
| `processing` | En preparación | `shipped`, `cancelled` |
| `shipped` | Enviada | `delivered` |
| `delivered` | Entregada | - |
| `cancelled` | Cancelada | - |
| `refunded` | Reembolsada | - |

---

## 💳 Métodos de Pago

- **Stripe** (stripe)
- **PayPal** (paypal)
- **MercadoPago** (mercadopago)
- **OpenPay** (openpay)
- **Efectivo** (cash) - Solo admin
- **Transferencia** (transfer) - Solo admin

---

## 📡 Endpoints de Usuario

### 1. **POST /orders** - Crear orden desde el carrito

```bash
curl -X POST "http://localhost:8000/orders" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "address_id": 1,
    "payment_method": "stripe",
    "notes": "Por favor tocar el timbre"
  }'
```

**Campos:**
- `address_id` (requerido): ID de la dirección de envío
- `payment_method` (opcional): Método de pago (default: "stripe")
- `notes` (opcional): Notas del cliente (max 500 caracteres)

**Proceso:**
1. Valida que el carrito no esté vacío
2. Valida que la dirección pertenezca al usuario
3. Valida stock de todos los productos
4. Crea la orden con snapshot de productos (nombre, precio)
5. Reduce el stock de los productos
6. Limpia el carrito de Redis
7. Retorna la orden creada en estado `pending`

**Cálculos automáticos:**
- `subtotal`: Suma de (precio × cantidad) de todos los productos
- `shipping_cost`: $100.00 MXN (fijo, puedes ajustarlo)
- `tax`: 16% IVA sobre el subtotal
- `total`: subtotal + shipping_cost + tax

**Respuesta exitosa:**
```json
{
  "success": true,
  "status_code": 201,
  "message": "Orden creada exitosamente",
  "data": {
    "id": 1,
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "address_id": 1,
    "payment_method": "stripe",
    "payment_id": null,
    "payment_status": null,
    "status": "pending",
    "subtotal": 850.00,
    "shipping_cost": 100.00,
    "tax": 136.00,
    "total": 1086.00,
    "notes": "Por favor tocar el timbre",
    "tracking_number": null,
    "order_items": [
      {
        "id": 1,
        "product_id": 5,
        "product_name": "Aceite de Argán Orgánico",
        "product_sku": "ARG-001",
        "quantity": 2,
        "unit_price": 350.00,
        "subtotal": 700.00
      },
      {
        "id": 2,
        "product_id": 8,
        "product_name": "Crema Facial Natural",
        "product_sku": "CRE-001",
        "quantity": 1,
        "unit_price": 150.00,
        "subtotal": 150.00
      }
    ],
    "created_at": "2025-11-19T10:30:00Z",
    "updated_at": null,
    "paid_at": null,
    "shipped_at": null,
    "delivered_at": null
  }
}
```

**Errores:**
- `400 EMPTY_CART`: El carrito está vacío
- `404 ADDRESS_NOT_FOUND`: La dirección no existe o no pertenece al usuario
- `404 PRODUCT_NOT_FOUND`: Algún producto del carrito no existe
- `400 INSUFFICIENT_STOCK`: Stock insuficiente para algún producto

---

### 2. **GET /orders** - Listar mis órdenes

```bash
curl -X GET "http://localhost:8000/orders?skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query params:**
- `skip` (opcional): Número de órdenes a omitir (default: 0)
- `limit` (opcional): Máximo de órdenes a retornar (default: 20)

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Órdenes obtenidas exitosamente",
  "data": {
    "orders": [
      {
        "id": 3,
        "status": "shipped",
        "payment_method": "stripe",
        "total": 1086.00,
        "items_count": 2,
        "created_at": "2025-11-19T10:30:00Z"
      },
      {
        "id": 2,
        "status": "delivered",
        "payment_method": "paypal",
        "total": 520.00,
        "items_count": 1,
        "created_at": "2025-11-15T14:20:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 3. **GET /orders/{order_id}** - Detalle de una orden

```bash
curl -X GET "http://localhost:8000/orders/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Respuesta:** Igual a la respuesta de crear orden (incluye todos los items y detalles)

**Errores:**
- `404 ORDER_NOT_FOUND`: La orden no existe o no pertenece al usuario

---

### 4. **POST /orders/{order_id}/cancel** - Cancelar orden

```bash
curl -X POST "http://localhost:8000/orders/1/cancel" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Restricciones:**
- Solo se puede cancelar si está en estado `pending` o `payment_pending`
- Restaura automáticamente el stock de los productos

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Orden cancelada exitosamente",
  "data": {
    "id": 1,
    "status": "cancelled",
    ...
  }
}
```

**Errores:**
- `404 ORDER_NOT_FOUND`: La orden no existe
- `400 CANNOT_CANCEL_ORDER`: No se puede cancelar en el estado actual

---

## 🛡️ Endpoints de Administración

**Nota:** Todos los endpoints de admin requieren que el usuario tenga `is_admin = true`

### 5. **GET /admin/orders** - Listar todas las órdenes (admin)

```bash
curl -X GET "http://localhost:8000/admin/orders?status=paid&limit=50" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Query params:**
- `skip` (opcional): Paginación (default: 0)
- `limit` (opcional): Límite por página (default: 20, max: 100)
- `status` (opcional): Filtrar por estado
- `payment_method` (opcional): Filtrar por método de pago
- `user_email` (opcional): Filtrar por email de usuario
- `date_from` (opcional): Fecha desde (YYYY-MM-DD)
- `date_to` (opcional): Fecha hasta (YYYY-MM-DD)
- `search` (opcional): Buscar por ID de orden o email

**Ejemplos de filtros:**
```bash
# Órdenes pagadas
curl -X GET "http://localhost:8000/admin/orders?status=paid" -H "Authorization: Bearer ADMIN_TOKEN"

# Órdenes de un usuario específico
curl -X GET "http://localhost:8000/admin/orders?user_email=juan@ejemplo.com" -H "Authorization: Bearer ADMIN_TOKEN"

# Órdenes del último mes
curl -X GET "http://localhost:8000/admin/orders?date_from=2025-10-19&date_to=2025-11-19" -H "Authorization: Bearer ADMIN_TOKEN"

# Buscar orden por ID
curl -X GET "http://localhost:8000/admin/orders?search=42" -H "Authorization: Bearer ADMIN_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Órdenes obtenidas exitosamente",
  "data": {
    "orders": [
      {
        "id": 1,
        "user_email": "juan@ejemplo.com",
        "user_name": "Juan Pérez",
        "status": "paid",
        "payment_method": "stripe",
        "total": 1086.00,
        "items_count": 2,
        "created_at": "2025-11-19T10:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 6. **GET /admin/orders/{order_id}** - Detalle completo (admin)

```bash
curl -X GET "http://localhost:8000/admin/orders/1" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Respuesta:** Incluye información adicional no visible para usuarios:
```json
{
  "success": true,
  "status_code": 200,
  "message": "Orden obtenida exitosamente",
  "data": {
    "id": 1,
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_email": "juan@ejemplo.com",
    "user_name": "Juan Pérez",
    "address_id": 1,
    "shipping_address": {
      "id": 1,
      "full_name": "Juan Pérez",
      "phone": "5512345678",
      "rfc": "PERJ850101ABC",
      "label": "Casa",
      "street": "Av. Principal 123",
      "city": "Ciudad de México",
      "state": "CDMX",
      "postal_code": "01000",
      "country": "México"
    },
    "payment_method": "stripe",
    "payment_id": "ch_3L4K5J6H7G8F9",
    "payment_status": "succeeded",
    "status": "paid",
    "subtotal": 850.00,
    "shipping_cost": 100.00,
    "tax": 136.00,
    "total": 1086.00,
    "notes": "Por favor tocar el timbre",
    "admin_notes": "Cliente VIP - priorizar envío",
    "tracking_number": "1234567890",
    "order_items": [...],
    "created_at": "2025-11-19T10:30:00Z",
    "updated_at": "2025-11-19T11:00:00Z",
    "paid_at": "2025-11-19T10:35:00Z",
    "shipped_at": null,
    "delivered_at": null
  }
}
```

---

### 7. **PATCH /admin/orders/{order_id}/status** - Actualizar estado (admin)

```bash
curl -X PATCH "http://localhost:8000/admin/orders/1/status" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "shipped",
    "admin_notes": "Enviado con FedEx",
    "tracking_number": "FDX1234567890"
  }'
```

**Campos:**
- `status` (requerido): Nuevo estado de la orden
- `admin_notes` (opcional): Notas internas (max 500 caracteres)
- `tracking_number` (opcional): Número de guía de envío (max 255 caracteres)

**Timestamps automáticos:**
- `paid` → Establece `paid_at`
- `shipped` → Establece `shipped_at`
- `delivered` → Establece `delivered_at`

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Estado actualizado de 'paid' a 'shipped'",
  "data": {
    "id": 1,
    "status": "shipped",
    "tracking_number": "FDX1234567890",
    "admin_notes": "Enviado con FedEx",
    "shipped_at": "2025-11-19T15:30:00Z",
    ...
  }
}
```

---

### 8. **GET /admin/orders/stats/summary** - Estadísticas y ganancias (admin)

```bash
curl -X GET "http://localhost:8000/admin/orders/stats/summary" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Estadísticas obtenidas exitosamente",
  "data": {
    "total_orders": 156,
    "total_revenue": 89450.00,
    "pending_orders": 5,
    "processing_orders": 12,
    "shipped_orders": 8,
    "delivered_orders": 125,
    "cancelled_orders": 6,
    "revenue_today": 2450.00,
    "revenue_this_week": 15230.00,
    "revenue_this_month": 42680.00,
    "revenue_this_year": 89450.00,
    "top_products": [
      {
        "product_id": 5,
        "product_name": "Aceite de Argán Orgánico",
        "product_sku": "ARG-001",
        "total_sold": 245,
        "total_revenue": 85750.00
      },
      {
        "product_id": 8,
        "product_name": "Crema Facial Natural",
        "product_sku": "CRE-001",
        "total_sold": 189,
        "total_revenue": 28350.00
      }
    ]
  }
}
```

**Incluye:**
- Total de órdenes por estado
- Ganancias totales (solo órdenes pagadas/entregadas)
- Ganancias por período (hoy, semana, mes, año)
- Top 5 productos más vendidos

---

### 9. **DELETE /admin/orders/{order_id}** - Eliminar orden (admin)

```bash
curl -X DELETE "http://localhost:8000/admin/orders/1" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Importante:** 
- Solo para casos excepcionales
- Restaura automáticamente el stock
- No se puede deshacer

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Orden eliminada exitosamente",
  "data": null
}
```

---

## 🔐 Seguridad

### Usuarios
- Solo pueden ver y gestionar sus propias órdenes
- Solo pueden cancelar órdenes en estado `pending` o `payment_pending`
- No pueden ver notas internas del admin

### Administradores
- Acceso completo a todas las órdenes
- Pueden cambiar estados libremente
- Pueden agregar notas internas y números de guía
- Pueden eliminar órdenes (con precaución)
- Tienen acceso a estadísticas y ganancias

---

## 🎯 Flujo de Compra Típico

### Usuario:
1. **Agregar productos al carrito** → `POST /cart/items`
2. **Revisar carrito** → `GET /cart`
3. **Seleccionar dirección** → `GET /addresses`
4. **Crear orden** → `POST /orders` (estado: `pending`)
5. **Procesar pago** → Frontend integra con Stripe/PayPal
6. **Webhook actualiza estado** → `payment_pending` → `paid`
7. **Seguimiento** → `GET /orders/{id}` (ver tracking_number)

### Administrador:
1. **Ver órdenes nuevas** → `GET /admin/orders?status=paid`
2. **Ver detalle completo** → `GET /admin/orders/{id}`
3. **Actualizar a procesando** → `PATCH /admin/orders/{id}/status` (status: `processing`)
4. **Preparar pedido** → Empacar productos
5. **Marcar como enviado** → `PATCH /admin/orders/{id}/status` (status: `shipped`, tracking_number: "...")
6. **Cliente recibe** → Actualizar a `delivered` manualmente o automáticamente

---

## 🔗 Integración con Pasarelas de Pago

### Flujo recomendado con Stripe:

1. **Frontend crea orden** → `POST /orders`
   - Retorna `order_id` y `total`
   
2. **Frontend crea PaymentIntent** → Stripe API
   ```javascript
   const paymentIntent = await stripe.paymentIntents.create({
     amount: order.total * 100, // Centavos
     currency: 'mxn',
     metadata: {
       order_id: order.id,
       user_id: user.id
     }
   });
   ```

3. **Frontend procesa pago** → Stripe Elements
   
4. **Webhook recibe evento** → `POST /webhooks/stripe`
   ```python
   @router.post("/webhooks/stripe")
   async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
       payload = await request.body()
       sig_header = request.headers.get('stripe-signature')
       
       event = stripe.Webhook.construct_event(
           payload, sig_header, WEBHOOK_SECRET
       )
       
       if event['type'] == 'payment_intent.succeeded':
           order_id = event['data']['object']['metadata']['order_id']
           payment_id = event['data']['object']['id']
           
           # Actualizar orden
           order = db.query(Order).filter(Order.id == order_id).first()
           order.status = OrderStatus.PAID
           order.payment_id = payment_id
           order.payment_status = "succeeded"
           order.paid_at = datetime.now()
           db.commit()
           
           # Opcional: enviar email de confirmación
   ```

5. **Frontend confirma** → Redirige a página de éxito

---

## 📊 Modelo de Base de Datos

### Tabla `orders`

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    address_id INTEGER NOT NULL REFERENCES addresses(id),
    
    -- Información de pago
    payment_method VARCHAR(50) NOT NULL,
    payment_id VARCHAR(255),
    payment_status VARCHAR(50),
    
    -- Estado y montos
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    subtotal DECIMAL(10, 2) NOT NULL,
    shipping_cost DECIMAL(10, 2) NOT NULL DEFAULT 0,
    tax DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    
    -- Datos adicionales
    notes TEXT,
    admin_notes TEXT,
    tracking_number VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    shipped_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_payment_id ON orders(payment_id);
```

### Tabla `order_items`

```sql
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    
    -- Snapshot del producto
    product_name VARCHAR(255) NOT NULL,
    product_sku VARCHAR(100),
    
    -- Cantidades y precios
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
```

---

## 💡 Casos de Uso

### Dashboard de Admin

```bash
# Ver resumen diario
curl -X GET "http://localhost:8000/admin/orders/stats/summary" -H "Authorization: Bearer ADMIN_TOKEN"

# Ver órdenes pendientes de procesar
curl -X GET "http://localhost:8000/admin/orders?status=paid&limit=50" -H "Authorization: Bearer ADMIN_TOKEN"

# Buscar órdenes de un cliente
curl -X GET "http://localhost:8000/admin/orders?user_email=cliente@ejemplo.com" -H "Authorization: Bearer ADMIN_TOKEN"
```

### Procesar Envío

```bash
# 1. Obtener detalle completo de la orden
curl -X GET "http://localhost:8000/admin/orders/42" -H "Authorization: Bearer ADMIN_TOKEN"

# 2. Marcar como enviado con número de guía
curl -X PATCH "http://localhost:8000/admin/orders/42/status" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "shipped",
    "tracking_number": "FDX9876543210",
    "admin_notes": "Enviado con FedEx - entrega estimada 3 días"
  }'
```

### Cliente Revisa Estado

```bash
# Ver todas mis órdenes
curl -X GET "http://localhost:8000/orders" -H "Authorization: Bearer USER_TOKEN"

# Ver detalle de una orden específica
curl -X GET "http://localhost:8000/orders/42" -H "Authorization: Bearer USER_TOKEN"
```

---

## ✅ Checklist de Implementación

| Funcionalidad | Estado |
|---------------|--------|
| Crear orden desde carrito | ✅ |
| Validación de stock | ✅ |
| Snapshot de productos | ✅ |
| Cálculo de totales (subtotal, tax, shipping) | ✅ |
| Limpieza de carrito | ✅ |
| Listar órdenes de usuario | ✅ |
| Ver detalle de orden | ✅ |
| Cancelar orden | ✅ |
| Restaurar stock al cancelar | ✅ |
| Listar todas las órdenes (admin) | ✅ |
| Filtros avanzados (admin) | ✅ |
| Actualizar estado (admin) | ✅ |
| Estadísticas y ganancias (admin) | ✅ |
| Top productos vendidos | ✅ |
| Timestamps automáticos | ✅ |
| Integración con webhooks | ⏳ Pendiente |
| Notificaciones por email | ⏳ Pendiente |

---

## 🚀 Próximos Pasos

1. **Integrar pasarela de pago:**
   - Crear endpoint `/webhooks/stripe`
   - Configurar webhook en Stripe Dashboard
   - Implementar verificación de firma
   - Actualizar estado de orden automáticamente

2. **Notificaciones por email:**
   - Email de confirmación al crear orden
   - Email al cambiar estado (shipped, delivered)
   - Email de factura (PDF con RFC)

3. **Facturación electrónica (CFDI):**
   - Integrar con PAC (Proveedor Autorizado de Certificación)
   - Generar XML de factura
   - Enviar al SAT
   - Entregar PDF y XML al cliente

4. **Reportes avanzados:**
   - Ganancias por producto
   - Ganancias por mes/año
   - Exportar a CSV/Excel
   - Gráficas de ventas

---

¡Sistema de órdenes completo y listo para integración! 🎉
