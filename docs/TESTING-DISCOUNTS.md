# 🧪 Guía de Pruebas - Sistema de Descuentos

## ✅ Checklist de Verificación

### 1. Verificar que la migración se aplicó

```bash
# Conectar a la base de datos
docker exec -it cisnatura_db psql -U user -d cisnatura

# Verificar que la tabla existe
\d admin_settings

# Ver el registro de configuraciones
SELECT id, maintenance_mode, global_discount_enabled, category_discounts FROM admin_settings;

# Salir
\q
```

**Resultado esperado:** Debe mostrar una tabla con un registro.

---

### 2. Aplicar Migración (si no existe la tabla)

```bash
cd /Users/alejandre/Developer/cisnatura-ecommerce/api-cisnatura

# Aplicar migración
docker exec cisnatura_app alembic upgrade head
```

---

### 3. Probar Configuración de Descuento por Categoría

#### A. Obtener token de admin

```bash
# Login como admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cisnatura.com",
    "password": "tu_password_admin"
  }'

# Copiar el access_token de la respuesta
```

#### B. Ver configuraciones actuales

```bash
curl http://localhost:8000/admin/settings \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

#### C. Aplicar descuento a categoría 1

```bash
curl -X POST http://localhost:8000/admin/settings/discount/category \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "1",
    "percentage": 20,
    "name": "Navidad"
  }'
```

**⚠️ IMPORTANTE:** El `category_id` debe ser **STRING** ("1"), no número (1).

#### D. Verificar que se guardó

```bash
curl http://localhost:8000/admin/settings \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  | jq '.category_discounts'
```

**Resultado esperado:**
```json
{
  "1": {
    "percentage": 20,
    "name": "Navidad"
  }
}
```

---

### 4. Verificar Descuento en Productos

#### A. Ver productos de categoría 1 SIN descuento

Primero elimina el descuento:
```bash
curl -X DELETE http://localhost:8000/admin/settings/discount/category/1 \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

Luego consulta productos:
```bash
curl "http://localhost:8000/products?category_id=1" | jq '.data.products[0]'
```

**Resultado esperado:**
```json
{
  "id": 1,
  "name": "Producto X",
  "original_price": 100.0,
  "price": 100.0,
  "has_discount": false
}
```

#### B. Aplicar descuento del 20%

```bash
curl -X POST http://localhost:8000/admin/settings/discount/category \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "1",
    "percentage": 20,
    "name": "Navidad"
  }'
```

#### C. Ver productos CON descuento

```bash
curl "http://localhost:8000/products?category_id=1" | jq '.data.products[0]'
```

**Resultado esperado:**
```json
{
  "id": 1,
  "name": "Producto X",
  "original_price": 100.0,
  "price": 80.0,
  "has_discount": true,
  "discount": {
    "discount_name": "Navidad",
    "discount_percentage": 20,
    "savings": 20.0,
    "discount_source": "category",
    "is_active": true
  }
}
```

---

### 5. Endpoint de Prueba de Descuentos

Usa este endpoint para debuggear:

```bash
# Probar descuento en producto ID 1
curl http://localhost:8000/admin/settings/test-discount/1 \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  | jq '.'
```

**Esto te muestra:**
- Información del producto
- Configuraciones actuales (descuentos activos)
- Cálculo detallado del precio final

---

## 🔍 Troubleshooting

### Problema 1: No se aplica el descuento

**Verificar:**
1. La tabla `admin_settings` existe
2. El `category_id` es STRING en el JSON
3. Los productos tienen `category_id` correcto
4. El servidor se reinició después de agregar el descuento

**Solución:**
```bash
# Verificar en base de datos
docker exec -it cisnatura_db psql -U user -d cisnatura -c \
  "SELECT id, name, category_id, price FROM products WHERE category_id = 1 LIMIT 5;"

# Ver configuraciones
docker exec -it cisnatura_db psql -U user -d cisnatura -c \
  "SELECT category_discounts FROM admin_settings;"
```

### Problema 2: Error 500 al obtener productos

**Causa:** La tabla `admin_settings` no existe o está vacía.

**Solución:**
```bash
# Aplicar migración
docker exec cisnatura_app alembic upgrade head

# O crear registro manualmente
docker exec -it cisnatura_db psql -U user -d cisnatura -c \
  "INSERT INTO admin_settings (
    id, maintenance_mode, shipping_price, 
    global_discount_enabled, global_discount_percentage,
    category_discounts, product_discounts, seasonal_offers,
    allow_user_registration, max_items_per_order,
    created_at, updated_at
  ) VALUES (
    gen_random_uuid(), false, 0.0,
    false, 0.0,
    '{}', '{}', '[]',
    true, 50,
    now(), now()
  );"
```

### Problema 3: category_id como número en vez de string

**Error:** Enviaste `category_id: 1` en vez de `category_id: "1"`

**Frontend correcto:**
```javascript
// ✅ CORRECTO
const response = await fetch('/admin/settings/discount/category', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    category_id: "1",  // STRING
    percentage: 20,
    name: "Navidad"
  })
});

// ❌ INCORRECTO
body: JSON.stringify({
  category_id: 1,  // NÚMERO - esto no funcionará
  percentage: 20,
  name: "Navidad"
})
```

---

## 🎯 Casos de Prueba Completos

### Caso 1: Descuento Global

```bash
# Aplicar 10% de descuento en TODOS los productos
curl -X PUT http://localhost:8000/admin/settings/discount/global \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "percentage": 10,
    "name": "Oferta de Verano"
  }'

# Ver productos
curl "http://localhost:8000/products?limit=3" | jq '.data.products[]'
```

### Caso 2: Descuento por Producto Específico

```bash
# Aplicar 30% de descuento al producto ID 5
curl -X POST http://localhost:8000/admin/settings/discount/product \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "5",
    "percentage": 30,
    "name": "Liquidación"
  }'

# Ver el producto
curl http://localhost:8000/products/5 | jq '.data'
```

### Caso 3: Oferta Temporal (Black Friday)

```bash
# Crear oferta del 24 al 30 de noviembre
curl -X POST http://localhost:8000/admin/settings/seasonal-offer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Black Friday 2025",
    "start_date": "2025-11-24",
    "end_date": "2025-11-30",
    "discount_percentage": 35,
    "category_ids": null,
    "product_ids": null
  }'

# Ver productos (solo aplicará si hoy está entre esas fechas)
curl "http://localhost:8000/products?limit=3" | jq '.data.products[]'
```

### Caso 4: Múltiples Descuentos (Verificar Prioridad)

```bash
# 1. Global: 10%
curl -X PUT http://localhost:8000/admin/settings/discount/global \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "percentage": 10, "name": "Global"}'

# 2. Categoría 1: 15%
curl -X POST http://localhost:8000/admin/settings/discount/category \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category_id": "1", "percentage": 15, "name": "Categoría"}'

# 3. Producto 5 de categoría 1: 25%
curl -X POST http://localhost:8000/admin/settings/discount/product \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "5", "percentage": 25, "name": "Producto"}'

# Ver producto 5 (debe aplicar 25%, el más específico)
curl http://localhost:8000/products/5 | jq '.data.discount'

# Ver producto 3 de categoría 1 (debe aplicar 15%)
curl http://localhost:8000/products/3 | jq '.data.discount'

# Ver producto 10 de otra categoría (debe aplicar 10% global)
curl http://localhost:8000/products/10 | jq '.data.discount'
```

---

## 📊 Verificación Final

### Script de Prueba Completo

```bash
#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🧪 Iniciando pruebas del sistema de descuentos..."

# 1. Login
echo "1️⃣ Obteniendo token de admin..."
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@cisnatura.com","password":"admin123"}' \
  | jq -r '.data.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo -e "${RED}❌ Error al obtener token${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Token obtenido${NC}"

# 2. Aplicar descuento a categoría
echo "2️⃣ Aplicando 20% de descuento a categoría 1..."
curl -s -X POST http://localhost:8000/admin/settings/discount/category \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category_id":"1","percentage":20,"name":"Navidad"}' > /dev/null
echo -e "${GREEN}✅ Descuento aplicado${NC}"

# 3. Verificar producto
echo "3️⃣ Verificando descuento en productos..."
DISCOUNT=$(curl -s "http://localhost:8000/products?category_id=1&limit=1" \
  | jq -r '.data.products[0].has_discount')

if [ "$DISCOUNT" = "true" ]; then
  echo -e "${GREEN}✅ ¡Descuento aplicado correctamente!${NC}"
  curl -s "http://localhost:8000/products?category_id=1&limit=1" \
    | jq '.data.products[0] | {name, original_price, price, discount}'
else
  echo -e "${RED}❌ Descuento no se aplicó${NC}"
fi

echo "✅ Pruebas completadas"
```

Guarda esto como `test_discounts.sh` y ejecuta:
```bash
chmod +x test_discounts.sh
./test_discounts.sh
```

---

## 🚨 Si Nada Funciona

```bash
# 1. Detener contenedores
docker-compose down

# 2. Reconstruir
docker-compose build

# 3. Levantar
docker-compose up -d

# 4. Aplicar migración
docker exec cisnatura_app alembic upgrade head

# 5. Verificar logs
docker logs cisnatura_app --tail=50

# 6. Verificar base de datos
docker exec -it cisnatura_db psql -U user -d cisnatura -c \
  "SELECT * FROM admin_settings;"
```
