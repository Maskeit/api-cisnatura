# Configuración de Webhooks de Stripe

## 🚀 Desarrollo Local con Stripe CLI

### 1. Iniciar el reenvío de webhooks

⚠️ **IMPORTANTE:** Debes incluir la ruta completa `/payments/webhook/stripe`:

```bash
stripe listen --forward-to localhost:8000/payments/webhook/stripe
```

Si solo usas `localhost:8000` recibirás **error 405 Method Not Allowed**.

Deberías ver algo como:
```
> Ready! You are using Stripe API Version [2025-11-17.clover]. 
> Your webhook signing secret is whsec_31716ce05cbe39b3aa129d83af3ed543273e5cf542a0c965bf792ef05fdf15e9 (^C to quit)
```

Y cuando lleguen eventos verás:
```
[200] POST http://localhost:8000/payments/webhook/stripe [evt_xxx]
```

**✅ Tu secret ya está configurado en `.env`:**
```
STRIPE_WEBHOOK_SECRET=whsec_31716ce05cbe39b3aa129d83af3ed543273e5cf542a0c965bf792ef05fdf15e9
```

### 2. Probar el webhook con un evento de prueba

En otra terminal, ejecuta:

```bash
stripe trigger checkout.session.completed
```

Esto enviará un evento simulado y verás los logs en tu API.

### 3. Ver logs de la API

```bash
cd api-cisnatura
docker-compose logs app -f | grep -E "Stripe|webhook|✅|❌|💰|🛒"
```

---

## 📡 Eventos de Stripe Procesados

El webhook procesa los siguientes eventos importantes:

### ✅ Eventos Críticos (Siempre se procesan)

1. **`checkout.session.completed`** - Pago completado con tarjeta
   - ✅ Crea la orden
   - ✅ Reduce stock
   - ✅ Limpia carrito
   - ✅ Marca orden como `PAID`

2. **`checkout.session.async_payment_succeeded`** - Pago asíncrono exitoso (OXXO, SPEI, etc.)
   - ✅ Crea la orden
   - ✅ Reduce stock
   - ✅ Limpia carrito
   - ✅ Marca orden como `PAID`

3. **`checkout.session.async_payment_failed`** - Pago asíncrono falló
   - ❌ Marca orden como `CANCELLED`
   - ↩️ Restaura stock (si existía orden)

4. **`charge.refunded`** - Reembolso procesado
   - 💰 Marca orden como `REFUNDED`
   - ↩️ Restaura stock

### ℹ️ Eventos Informativos (Solo logging)

- `payment_intent.succeeded` - Confirmación adicional
- `payment_intent.payment_failed` - Fallo de payment intent
- `charge.succeeded` - Cargo exitoso
- `charge.updated` - Actualización de cargo
- `payment_intent.created` - Payment intent creado

### 🚫 Eventos NO Escuchados

Para un e-commerce simple **NO necesitas**:
- `customer.*` - Gestión de clientes (usas tu propia DB)
- `invoice.*` - Facturas/suscripciones
- `subscription.*` - Suscripciones recurrentes
- `payout.*` - Pagos a tu cuenta bancaria
- `balance.*` - Balance de Stripe

---

## 📋 Flujo Completo

1. **Usuario inicia checkout**
   - Frontend llama a `POST /payments/stripe/create-checkout-session`
   - Backend crea sesión de Stripe con metadata (user_id, address_id, etc.)
   - Retorna `checkout_url` para redirigir al usuario

2. **Usuario paga en Stripe**
   - Stripe procesa el pago
   - Si es exitoso, redirige a: `http://localhost:3000/checkout/stripe/success?session_id=cs_test_xxx`

3. **Stripe envía webhook**
   - Evento: `checkout.session.completed`
   - Payload incluye session_id, payment_status, metadata
   - Backend valida firma (en producción)

4. **Backend procesa el webhook**
   - Lee metadata (user_id, address_id, totales)
   - Verifica que no exista orden duplicada
   - Obtiene carrito de Redis
   - Crea orden con status `PAID`
   - Reduce stock de productos
   - Limpia carrito de Redis
   - (TODO) Envía email de confirmación

5. **Usuario ve orden confirmada**
   - Frontend consulta `GET /orders/` y ve la nueva orden
   - El carrito está vacío

---

## 🔍 Debugging

### Ver todos los eventos de Stripe
```bash
stripe events list --limit 10
```

### Ver detalles de un evento específico
```bash
stripe events retrieve evt_xxx
```

### Ver sesiones de checkout recientes
```bash
stripe checkout sessions list --limit 10
```

### Ver una sesión específica
```bash
stripe checkout sessions retrieve cs_test_xxx
```

### Logs de la API con colores
```bash
docker-compose logs app -f
```

Busca estos emojis para seguir el flujo:
- 📥 Webhook recibido
- ✅ Checkout completado
- 💳 Payment status
- 💰 Monto del pago
- 📦 Metadata
- 🛒 Creando orden
- 🗑️ Limpiando carrito
- ❌ Errores

---

## 🚨 Errores Comunes

### 1. "Cart empty for user on Stripe webhook"
**Causa:** El carrito ya fue limpiado o el user_id no coincide.

**Solución:** Verifica que el metadata tenga el user_id correcto:
```bash
stripe checkout sessions retrieve cs_test_xxx
```

### 2. "Order already exists for Stripe session"
**Causa:** El webhook se ejecutó dos veces (Stripe reintenta si no recibe 200 OK).

**Solución:** Esto es normal, el sistema detecta duplicados automáticamente.

### 3. "No user_id in metadata"
**Causa:** La sesión se creó sin metadata o hubo un error.

**Solución:** Revisa que el endpoint `/stripe/create-checkout-session` esté pasando el metadata correctamente.

### 4. Formato de precio incorrecto ($5.65 en vez de $565.00)
**Causa:** El frontend está mostrando los centavos en vez de pesos.

**Solución:** Stripe maneja montos en centavos. El backend ya convierte:
- Al crear sesión: `amount * 100` (pesos → centavos)
- Al leer sesión: `amount / 100` (centavos → pesos)

Verifica que el frontend divida entre 100 si recibe el monto de Stripe directamente.

---

## 🌐 Producción

### 1. Configurar webhook en Stripe Dashboard

1. Ve a: https://dashboard.stripe.com/webhooks
2. Clic en "Add endpoint"
3. URL: `https://tudominio.com/payments/webhook/stripe`
4. Selecciona eventos:
   - `checkout.session.completed` ✅
   - `payment_intent.succeeded` (opcional)
   - `charge.refunded` (opcional)

5. Copia el **Signing secret** (empieza con `whsec_`)
6. Actualiza tu `.env` de producción:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_xxx_produccion
   ```

### 2. Variables de entorno

```bash
# .env producción
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_xxx  # ⚠️ Live key, no test
STRIPE_WEBHOOK_SECRET=whsec_xxx_produccion
```

### 3. Seguridad

⚠️ **IMPORTANTE:** En producción, la validación de firma está activa:
```python
if webhook_secret and signature:
    event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
```

Esto previene ataques de spoofing. Nunca desactives esto en producción.

---

## ✅ Checklist

- [ ] Stripe CLI instalado y autenticado
- [ ] API corriendo en `localhost:8000`
- [ ] Frontend corriendo en `localhost:3000`
- [ ] Webhook secret en `.env`
- [ ] `stripe listen --forward-to localhost:8000/payments/webhook/stripe` corriendo
- [ ] Carrito con productos
- [ ] Dirección de envío configurada
- [ ] Logs de la API visibles

---

## 🧪 Prueba Completa

```bash
# Terminal 1: Logs de la API
cd api-cisnatura
docker-compose logs app -f | grep -E "Stripe|webhook|✅|❌"

# Terminal 2: Stripe CLI
stripe listen --forward-to localhost:8000/payments/webhook/stripe

# Terminal 3: Reiniciar API (si hiciste cambios)
cd api-cisnatura
docker-compose restart app
```

Luego en el frontend:
1. Agrega productos al carrito
2. Ve a checkout
3. Paga con tarjeta de prueba: `4242 4242 4242 4242`
4. Observa los logs en ambas terminales
5. Verifica que la orden aparezca en `/orders/`
6. Verifica que el carrito esté vacío

---

## 📞 Soporte

Si algo no funciona, revisa los logs con este comando:
```bash
docker-compose logs app --tail=100 | grep -A 5 -B 5 "Stripe\|webhook"
```

Y comparte la salida para diagnosticar el problema.
