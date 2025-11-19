# Carrito de Compras con Redis

## ✅ Cambios Realizados

Se ha migrado el sistema de carritos de **PostgreSQL** a **Redis** para experimentar con almacenamiento volátil y alta velocidad.

### Arquitectura Actualizada

**Antes (PostgreSQL):**
- Carrito persistido en tablas `carts` y `cart_items`
- Datos permanentes en base de datos
- Relaciones con usuarios y productos

**Ahora (Redis):**
- Carrito almacenado en Redis con clave `cart:{user_id}`
- Datos volátiles (expiran en 7 días automáticamente)
- PostgreSQL solo se usa para validar productos y obtener su información

### Ventajas de Redis para Carritos

✅ **Velocidad**: Operaciones en memoria (sub-milisegundo)  
✅ **Simplicidad**: No requiere relaciones ni migraciones  
✅ **Auto-expiración**: Carritos abandonados se limpian automáticamente  
✅ **Escalabilidad**: Ideal para alta concurrencia  

### Consideraciones

⚠️ **Volátil**: Si Redis se reinicia sin persistencia, se pierden los carritos  
⚠️ **Temporal**: Expiran en 7 días (configurable en `CartService`)  
⚠️ **Migración a Pedido**: Al confirmar compra, se debe mover a PostgreSQL (`orders`)  

---

## 🔧 Estructura de Datos en Redis

### Clave del Carrito
```
cart:{user_id}
```

### Valor (JSON)
```json
{
  "1": {
    "product_id": 1,
    "quantity": 2
  },
  "3": {
    "product_id": 3,
    "quantity": 1
  }
}
```

### Expiración
- **TTL**: 7 días (604,800 segundos)
- Se resetea en cada operación (`add_item`, `update_item_quantity`)

---

## 📡 Endpoints del Carrito

### 1. **GET /cart** - Obtener carrito completo
```bash
curl -X GET "http://localhost:8000/cart" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Carrito obtenido exitosamente",
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "items": [
      {
        "product_id": 1,
        "quantity": 2,
        "product": {
          "id": 1,
          "name": "Producto A",
          "slug": "producto-a",
          "price": 29.99,
          "stock": 50,
          "image_url": "/products/producto-a.jpg",
          "is_active": true
        },
        "subtotal": 59.98
      }
    ],
    "total_items": 2,
    "total_amount": 59.98
  }
}
```

---

### 2. **GET /cart/summary** - Resumen (totales)
```bash
curl -X GET "http://localhost:8000/cart/summary" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Respuesta:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Resumen del carrito",
  "data": {
    "total_items": 3,
    "total_amount": 89.97
  }
}
```

**Uso:** Para mostrar el badge del carrito sin cargar todos los productos.

---

### 3. **POST /cart/items** - Agregar producto
```bash
curl -X POST "http://localhost:8000/cart/items" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2
  }'
```

**Validaciones:**
- ✅ Producto debe existir y estar activo
- ✅ Stock suficiente disponible
- ✅ Si ya existe, incrementa cantidad automáticamente
- ✅ Cantidad: 1-100 (validado por Pydantic)

**Respuesta:** Carrito completo actualizado

---

### 4. **PUT /cart/items/{product_id}** - Actualizar cantidad
```bash
curl -X PUT "http://localhost:8000/cart/items/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 5
  }'
```

**Cambio importante:** Ahora se usa `product_id` como parámetro en la URL (antes era `item_id`).

**Validaciones:**
- ✅ Producto debe estar en el carrito
- ✅ Stock suficiente disponible
- ✅ Cantidad: 1-100

---

### 5. **DELETE /cart/items/{product_id}** - Eliminar producto
```bash
curl -X DELETE "http://localhost:8000/cart/items/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Respuesta:** Carrito actualizado sin ese producto

---

### 6. **DELETE /cart/clear** - Vaciar carrito
```bash
curl -X DELETE "http://localhost:8000/cart/clear" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Respuesta:** Carrito vacío

---

## 🧪 Probar con Redis CLI

### Ver todos los carritos
```bash
docker exec cisnatura_redis_dev redis-cli KEYS "cart:*"
```

### Ver carrito de un usuario específico
```bash
docker exec cisnatura_redis_dev redis-cli GET "cart:{user_id}"
```

### Ver tiempo de expiración (TTL)
```bash
docker exec cisnatura_redis_dev redis-cli TTL "cart:{user_id}"
```
**Resultado:** Segundos restantes hasta expirar (604800 = 7 días)

### Limpiar carrito manualmente
```bash
docker exec cisnatura_redis_dev redis-cli DEL "cart:{user_id}"
```

---

## 🔄 Flujo Completo de Compra (Futuro)

Cuando el usuario confirme la compra, deberás:

1. **Leer carrito desde Redis** (`CartService.get_cart()`)
2. **Validar stock actualizado** (por si cambió desde que agregó al carrito)
3. **Crear pedido en PostgreSQL** (tabla `orders` y `order_items`)
4. **Reducir stock** en productos
5. **Limpiar carrito en Redis** (`CartService.clear_cart()`)

Esto asegura que los datos importantes (pedidos) persistan en PostgreSQL, mientras el carrito temporal vive en Redis.

---

## 🐞 Debugging

### Logs de la aplicación
```bash
docker logs -f cisnatura_app_dev
```

### Verificar Redis funciona
```bash
docker exec cisnatura_redis_dev redis-cli PING
# Debe responder: PONG
```

### Reiniciar servicios
```bash
docker-compose restart
```

---

## 📝 Archivos Modificados

### `/app/routes/carts.py`
- ✅ Reemplazado PostgreSQL por Redis (`CartService`)
- ✅ Función `format_cart_response()` ahora consulta Redis primero
- ✅ PostgreSQL solo se usa para obtener datos de productos (nombre, precio, stock)
- ✅ Cambio en rutas: `/items/{product_id}` en vez de `/items/{item_id}`

### `/app/core/redis_service.py`
- Clase `CartService` ya existía pero no se usaba
- Ahora es el motor principal del carrito
- Métodos: `add_item()`, `get_cart()`, `update_item_quantity()`, `remove_item()`, `clear_cart()`

---

## 🚀 Próximos Pasos

1. **Probar todos los endpoints** con Postman o curl
2. **Verificar persistencia** en Redis con `redis-cli`
3. **Implementar checkout** que migre carrito → pedido (PostgreSQL)
4. **Considerar Redis Persistence** (RDB/AOF) si quieres durabilidad

¡Ahora puedes experimentar con la velocidad de Redis! 🚀
