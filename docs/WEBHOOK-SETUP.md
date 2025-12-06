# Configuración de Webhooks de MercadoPago

## 🔧 Configuración en Desarrollo (Localhost)

### 1. Exponer tu servidor local con ngrok

```bash
# Ejecutar el script (abre una nueva terminal)
./start-ngrok.sh
```

Esto te mostrará una URL como: `https://abc123.ngrok.io`

### 2. Configurar el Webhook en MercadoPago

1. Ve a: https://www.mercadopago.com.mx/developers/panel/app
2. Selecciona tu aplicación de **prueba**
3. En el menú lateral, click en **"Webhooks"**
4. Click en **"Configurar notificaciones"**
5. Pega la URL completa del webhook:
   ```
   https://TU_URL_NGROK.ngrok.io/payments/webhook/mercadopago
   ```
   Ejemplo real:
   ```
   https://abc123.ngrok.io/payments/webhook/mercadopago
   ```
6. Selecciona el evento: **"Pagos"** → Marca **"payment.updated"**
7. Click en **"Guardar"**

### 3. Probar el Webhook

MercadoPago tiene una opción para **"Simular notificación"** en el panel de webhooks:

1. En la configuración del webhook
2. Click en **"Probar"** o **"Simular notificación"**
3. Deberías ver status **200 OK**

## 🚀 Configuración en Producción

### 1. Usa tu dominio real

```
https://api.tudominio.com/payments/webhook/mercadopago
```

### 2. Configuración SSL

Asegúrate de que tu servidor tenga **HTTPS** configurado. MercadoPago **rechaza URLs HTTP** en producción.

### 3. Validación de Firma (Recomendado)

El webhook incluye headers de seguridad:

```
x-signature: firma_del_webhook
x-request-id: id_unico
```

Para validar la firma, necesitas implementar:

```python
# En app/core/payment_providers/mercadopago.py
def validate_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
    import hmac
    import hashlib
    
    computed_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)
```

Luego en el endpoint:

```python
signature = request.headers.get("x-signature", "")
if not payment_service.provider.validate_webhook(
    payload,
    signature,
    settings.MERCADOPAGO_WEBHOOK_SECRET
):
    raise HTTPException(401, "Invalid signature")
```

## 📋 Eventos que envía MercadoPago

El webhook recibirá notificaciones para estos eventos:

```json
{
  "action": "payment.updated",
  "api_version": "v1",
  "data": {"id": "123456"},
  "date_created": "2021-11-01T02:02:02Z",
  "id": "123456",
  "live_mode": false,
  "type": "payment",
  "user_id": 389357324
}
```

### Estados de pago importantes:

- `approved` → Pago aprobado (se crea la orden)
- `pending` → Pago pendiente (ej: boleto bancario)
- `in_process` → Pago en revisión
- `rejected` → Pago rechazado
- `cancelled` → Pago cancelado
- `refunded` → Pago reembolsado
- `charged_back` → Contracargo

## 🧪 Probar el Flujo Completo

### 1. Agregar productos al carrito
```bash
POST /cart/items
{
  "product_id": 1,
  "quantity": 2
}
```

### 2. Crear checkout desde el carrito
```bash
POST /payments/create-from-cart
{
  "address_id": 1,
  "payment_method": "mercadopago"
}
```

### 3. Pagar en MercadoPago
- Usar tarjeta de prueba: `4009 1753 3280 7950`
- CVV: cualquier 3 dígitos
- Fecha: cualquier fecha futura

### 4. MercadoPago envía webhook
- Tu servidor recibe la notificación
- Se crea la orden automáticamente
- Se reduce el stock
- Se limpia el carrito

## 🐛 Debugging

### Ver logs del webhook

```bash
docker-compose logs app -f | grep webhook
```

### Logs esperados:

```
INFO: MercadoPago webhook received: {'type': 'payment', 'data': {'id': '123456'}}
INFO: Payment 123456 status: approved, ref: cart_user_123_1234567890
INFO: Order 1 created from cart via webhook for payment 123456
```

## ❌ Errores Comunes

### Error 405 - Method Not Allowed
- **Causa**: La URL del webhook está mal o el servidor no está accesible
- **Solución**: Verifica que la URL sea exacta y que ngrok esté corriendo

### Error 401 - Unauthorized
- **Causa**: La firma del webhook no es válida
- **Solución**: Desactiva la validación de firma temporalmente para pruebas

### Error 500 - Internal Server Error
- **Causa**: Error en el código del webhook
- **Solución**: Revisa los logs con `docker-compose logs app`

### Webhook no recibe notificaciones
- **Causa**: ngrok se reinició y la URL cambió
- **Solución**: Actualiza la URL en el panel de MercadoPago

## 📝 Variables de Entorno

Asegúrate de tener configuradas en `.env`:

```bash
# MercadoPago
MERCADOPAGO_ACCESS_TOKEN_TEST=APP_USR-xxx
MERCADOPAGO_WEBHOOK_SECRET_TEST=tu_webhook_secret
MERCADOPAGO_ENVIRONMENT=test

# Frontend
FRONTEND_URL=http://localhost:3000
```

## 🔗 Enlaces Útiles

- Panel de MercadoPago: https://www.mercadopago.com.mx/developers/panel/app
- Documentación de Webhooks: https://www.mercadopago.com.mx/developers/es/docs/your-integrations/notifications/webhooks
- Tarjetas de prueba: https://www.mercadopago.com.mx/developers/es/docs/checkout-pro/additional-content/test-cards
- ngrok Dashboard: https://dashboard.ngrok.com/
