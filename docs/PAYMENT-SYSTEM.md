# Sistema de Pagos - Multi-Provider

## Arquitectura

El sistema de pagos está diseñado con una arquitectura flexible que permite integrar múltiples proveedores de pago (MercadoPago, Stripe, etc.) sin cambiar el código de la aplicación.

### Componentes

1. **`PaymentProvider` (Abstract Class)**: Define la interfaz común que todos los proveedores deben implementar
2. **`PaymentService` (Factory)**: Selecciona e inicializa el proveedor según la configuración
3. **Implementaciones específicas**: Cada proveedor (MercadoPago, Stripe) implementa la interfaz

```
┌─────────────────────┐
│   PaymentService    │  ← Factory Pattern
│    (Singleton)      │
└──────────┬──────────┘
           │
           ├─────────────┐
           │             │
    ┌──────▼───────┐  ┌─▼──────────┐
    │ MercadoPago  │  │   Stripe   │
    │   Provider   │  │  Provider  │
    └──────────────┘  └────────────┘
```

## Configuración

### Variables de Entorno (.env)

```bash
# Proveedor activo
PAYMENT_PROVIDER=mercadopago  # o 'stripe'

# MercadoPago
MERCADOPAGO_ACCESS_TOKEN_TEST=TEST-your-test-access-token
MERCADOPAGO_ACCESS_TOKEN_PROD=your-production-access-token
MERCADOPAGO_ENVIRONMENT=test  # o 'production'

# Stripe (futuro)
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Inicialización (main.py)

El servicio se inicializa automáticamente al arrancar la aplicación:

```python
from core.payment_service import payment_service

# Ya está inicializado, listo para usar
payment_service.initialize_payment_service()
```

## Uso en Endpoints

### Crear un Pago

```python
from core.payment_service import payment_service
from decimal import Decimal

# Crear preferencia de pago
result = payment_service.provider.create_payment(
    amount=Decimal("150.00"),
    currency="MXN",
    description="Orden #12345 - Productos Cisnatura",
    order_id="12345",
    customer_email="cliente@example.com",
    metadata={
        "success_url": "https://cisnatura.com/success",
        "failure_url": "https://cisnatura.com/failure",
        "pending_url": "https://cisnatura.com/pending"
    }
)

if result["success"]:
    # Redirigir al usuario a la URL de pago
    checkout_url = result["checkout_url"]
    payment_id = result["payment_id"]
else:
    # Manejar error
    error = result["error"]
```

### Consultar Estado de Pago

```python
status_result = payment_service.provider.get_payment_status(payment_id)

if status_result["success"]:
    status = status_result["status"]  # approved, pending, rejected, etc.
    amount = status_result["amount"]
    order_id = status_result["external_reference"]
```

### Cancelar Pago

```python
cancel_result = payment_service.provider.cancel_payment(payment_id)
```

### Reembolso

```python
# Reembolso total
refund_result = payment_service.provider.refund_payment(payment_id)

# Reembolso parcial
refund_result = payment_service.provider.refund_payment(
    payment_id,
    amount=Decimal("50.00")
)
```

### Validar Webhook

```python
from fastapi import Request

@app.post("/webhooks/payment")
async def payment_webhook(request: Request):
    # Obtener firma del header
    signature = request.headers.get("x-signature")
    
    # Leer el payload
    payload = await request.body()
    
    # Validar firma
    is_valid = payment_service.provider.validate_webhook(
        payload=payload,
        signature=signature,
        secret=settings.MERCADOPAGO_WEBHOOK_SECRET
    )
    
    if is_valid:
        # Procesar evento
        data = await request.json()
        # ...
    else:
        return {"error": "Invalid signature"}
```

## MercadoPago - Detalles Específicos

### Flujo de Pago

1. **Crear Preferencia**: El backend crea una preferencia con `create_payment()`
2. **Redirigir al Checkout**: El frontend redirige al usuario a `checkout_url`
3. **Usuario paga**: El usuario completa el pago en MercadoPago
4. **Notificación**: MercadoPago envía webhooks con el resultado
5. **Confirmar Orden**: El backend procesa el webhook y actualiza la orden

### Estados de Pago

- `approved`: Pago aprobado
- `pending`: Pago pendiente (puede tardar días)
- `in_process`: En proceso de aprobación
- `rejected`: Pago rechazado
- `cancelled`: Pago cancelado
- `refunded`: Pago reembolsado

### URLs de Retorno

Configurar en `metadata` al crear el pago:

```python
metadata = {
    "success_url": f"{FRONTEND_URL}/orders/{order_id}/success",
    "failure_url": f"{FRONTEND_URL}/orders/{order_id}/failure",
    "pending_url": f"{FRONTEND_URL}/orders/{order_id}/pending"
}
```

### Webhooks

MercadoPago envía notificaciones a tu endpoint cuando cambia el estado del pago.

**Endpoint recomendado**: `POST /api/webhooks/mercadopago`

**Headers importantes**:
- `x-signature`: Firma HMAC-SHA256 del payload
- `x-request-id`: ID único de la notificación

**Tipos de notificación**:
- `payment`: Estado de pago cambió
- `merchant_order`: Orden cambió

### Modo Test vs Production

**Test**:
- Usa `MERCADOPAGO_ACCESS_TOKEN_TEST`
- URLs de prueba: `sandbox_init_point`
- Tarjetas de prueba: https://www.mercadopago.com.mx/developers/es/docs/checkout-pro/additional-content/test-cards

**Production**:
- Usa `MERCADOPAGO_ACCESS_TOKEN_PROD`
- URLs reales: `init_point`
- Pagos reales con tarjetas verdaderas

## Agregar Nuevo Proveedor

Para agregar un nuevo proveedor (ej: PayPal, Stripe):

1. **Crear implementación**: `app/core/payment_providers/paypal.py`

```python
from core.payment_service import PaymentProvider

class PayPalProvider(PaymentProvider):
    def initialize(self):
        # Inicializar SDK de PayPal
        pass
    
    def create_payment(self, ...):
        # Implementar creación de pago
        pass
    
    # ... implementar otros métodos
```

2. **Agregar al factory**: En `payment_service.py`

```python
def initialize(self, provider_name: str, **config):
    if provider_name == "paypal":
        from core.payment_providers.paypal import PayPalProvider
        self._provider = PayPalProvider(**config)
    # ...
```

3. **Agregar configuración**: En `.env` y `config.py`

```python
PAYMENT_PROVIDER=paypal
PAYPAL_CLIENT_ID=...
PAYPAL_SECRET=...
```

## Ventajas de esta Arquitectura

✅ **Desacoplamiento**: Cambiar de proveedor solo requiere cambiar 1 variable de entorno  
✅ **Extensibilidad**: Agregar nuevos proveedores sin modificar código existente  
✅ **Testeable**: Fácil crear mocks de proveedores para testing  
✅ **Consistencia**: Todos los proveedores usan la misma interfaz  
✅ **Mantenibilidad**: Cada proveedor en su propio archivo  

## Ejemplo Completo: Endpoint de Pago

```python
from fastapi import APIRouter, Depends, HTTPException
from core.payment_service import payment_service
from core.database import get_db
from models.order import Order
from decimal import Decimal

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/create")
async def create_payment(
    order_id: str,
    db: Session = Depends(get_db)
):
    # Buscar orden
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    
    # Crear pago con el proveedor activo
    result = payment_service.provider.create_payment(
        amount=Decimal(str(order.total_amount)),
        currency="MXN",
        description=f"Orden #{order.id}",
        order_id=str(order.id),
        customer_email=order.user.email,
        metadata={
            "success_url": f"{settings.FRONTEND_URL}/orders/{order.id}/success",
            "failure_url": f"{settings.FRONTEND_URL}/orders/{order.id}/failure",
            "pending_url": f"{settings.FRONTEND_URL}/orders/{order.id}/pending"
        }
    )
    
    if result["success"]:
        # Guardar payment_id en la orden
        order.payment_id = result["payment_id"]
        order.payment_status = "pending"
        db.commit()
        
        return {
            "success": True,
            "checkout_url": result["checkout_url"],
            "payment_id": result["payment_id"]
        }
    else:
        raise HTTPException(500, result["error"])
```

## Testing

Para probar MercadoPago en modo test:

1. Usa `MERCADOPAGO_ENVIRONMENT=test`
2. Configura `MERCADOPAGO_ACCESS_TOKEN_TEST` con tu token de prueba
3. Usa las tarjetas de prueba de MercadoPago
4. Las URLs de sandbox permiten simular aprobaciones/rechazos

## Recursos

- **MercadoPago Docs**: https://www.mercadopago.com.mx/developers
- **SDK Python**: https://github.com/mercadopago/sdk-python
- **Tarjetas de Prueba**: https://www.mercadopago.com.mx/developers/es/docs/checkout-pro/additional-content/test-cards
