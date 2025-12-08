# Sistema de Notificaciones por Correo - Órdenes

Sistema completo de notificaciones por correo para órdenes de compra, sin requerir acción del usuario.

## 📦 Archivos Creados

### 1. Servicio de Notificaciones
**`app/core/notification_email_service.py`**
- Extiende `EmailService` para reutilizar configuración SMTP
- Tres tipos de notificaciones implementadas:
  - **Cliente - Confirmación de Pedido**: Envía resumen completo después del pago
  - **Admin - Nueva Orden**: Notifica al admin de orden pagada
  - **Cliente - Pedido Enviado**: Notifica cuando se marca como enviado con tracking

### 2. Schemas
**`app/schemas/order_notifications.py`**
- `ShippingNotificationRequest`: Para notificar envío con tracking
- `NotificationResponse`: Respuesta estándar de notificaciones

## 🔄 Flujo de Notificaciones

### Al Completar Pago (Stripe Webhook)
**`app/routes/payments.py` - `_process_payment_success()`**

1. Crea la orden en base de datos
2. Envía **correo al cliente** con:
   - Número de orden (ORD-YYYYMM-####)
   - Lista de productos
   - Totales (subtotal + envío + total)
   - Dirección de envío
   - Mensaje: "Te enviaremos tu guía pronto"
3. Envía **correo al admin** con:
   - Número de orden
   - Cliente (nombre + email)
   - Total pagado
   - Cantidad de productos
   - CTA: "Ver Orden en Admin"

### Al Marcar Orden como Enviada (Admin)
**`POST /admin/orders/{order_id}/notify-shipping`**

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `tracking_number` (string, required): Número de guía
- `shipping_carrier` (string, required): Nombre de la paquetería
- `tracking_url` (string, optional): URL de rastreo
- `admin_notes` (string, optional): Mensaje personalizado para el cliente
- `tracking_pdf` (file, optional): Archivo PDF de la guía (máximo 5MB)

**Ejemplo con cURL:**
```bash
curl -X POST "http://localhost:8000/admin/orders/123/notify-shipping" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "tracking_number=1234567890" \
  -F "shipping_carrier=FedEx" \
  -F "tracking_url=https://fedex.com/track?n=1234567890" \
  -F "admin_notes=Tu paquete llegará en 3-5 días hábiles" \
  -F "tracking_pdf=@guia.pdf"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Orden marcada como enviada y notificación enviada al cliente",
  "email_sent": true,
  "recipient": "cliente@example.com"
}
```

**Funcionalidad:**
1. Valida orden pagada
2. Guarda PDF de guía en `uploads/tracking_guides/` (si se proporciona)
3. Actualiza `tracking_number` en la orden
4. Agrega `admin_notes` a las notas internas (si se proporcionan)
5. Cambia estado a `SHIPPED`
6. Envía **correo al cliente** con:
   - Número de orden
   - Paquetería
   - Número de guía
   - Mensaje personalizado (si admin_notes)
   - Botón "Rastrear mi Pedido" (si tracking_url)
   - PDF de guía adjunto (si tracking_pdf)
   - Tiempo estimado de entrega

## 📧 Templates de Correos

Todos los correos tienen:
- ✅ Diseño HTML responsive
- ✅ Versión en texto plano (fallback)
- ✅ Gradientes y colores profesionales
- ✅ CTAs (Call-to-Action) con botones
- ✅ Footer con nota "correo de notificación"

### 1. Confirmación de Pedido (Cliente)
- **Asunto:** `✅ Confirmación de pedido #ORD-202512-0001 - Cisnatura`
- **Header:** Verde con checkmark
- **Contenido:**
  - Saludo personalizado
  - Número de orden destacado
  - Tabla de productos con subtotales
  - Resumen de pago (subtotal, envío, total)
  - Dirección de envío
  - Próximos pasos
  - Botón "Ver mis pedidos"

### 2. Nueva Orden (Admin)
- **Asunto:** `🔔 Nueva Orden #ORD-202512-0001 - $1,234.56 MXN`
- **Header:** Azul con campana
- **Contenido:**
  - Número de orden + total destacados
  - Detalles del cliente (nombre, email)
  - Cantidad de productos
  - Método de pago
  - Badge "PAGADA"
  - Alerta de acción requerida
  - Botón "Ver Orden en Admin"

### 3. Pedido Enviado (Cliente)
- **Asunto:** `📦 Tu pedido #ORD-202512-0001 ha sido enviado`
- **Header:** Morado con paquete
- **Contenido:**
  - Mensaje de pedido en camino
  - Paquetería
  - Número de guía destacado
  - **Mensaje personalizado del admin** (si admin_notes) en caja amarilla destacada
  - Botón "Rastrear mi Pedido" (opcional)
  - **PDF de guía adjunto** (si tracking_pdf)
  - Tiempo estimado de entrega (3-5 días)

## ⚙️ Configuración

### Variables de Entorno (.env)
```env
# SMTP Configuration (MailHog para desarrollo)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
FROM_EMAIL=noreply@cisnatura.com
FROM_NAME=Cisnatura
FRONTEND_URL=http://localhost:3000
```

### Producción
Para producción, actualizar con credenciales reales:
```env
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465  # SSL directo
SMTP_USER=tu-email@dominio.com
SMTP_PASSWORD=tu-contraseña
FROM_EMAIL=tu-email@dominio.com
FROM_NAME=Cisnatura
FRONTEND_URL=https://tu-dominio.com
```

## 🧪 Pruebas

### 1. Probar con MailHog
```bash
# MailHog debe estar corriendo
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Ver correos en: http://localhost:8025
```

### 2. Flujo de Prueba Completo

#### A. Prueba de Orden Nueva
1. Crear orden mediante Stripe Checkout
2. Webhook procesa pago exitoso
3. Verificar en MailHog:
   - Correo al cliente con confirmación
   - Correo al admin con notificación

#### B. Prueba de Envío
```bash
# Endpoint
POST /admin/orders/1/notify-shipping

# Body
{
  "order_id": 1,
  "tracking_number": "TEST123456",
  "shipping_carrier": "FedEx",
  "tracking_url": "https://fedex.com/track"
}
```

Verificar en MailHog: correo al cliente con tracking

## 📝 Notas Importantes

1. **Errores de Email No Bloquean Operaciones**
   - Si falla el envío, se loguea error pero la orden se crea igual
   - `email_sent: false` en respuesta indica fallo

2. **Email del Admin**
   - Se busca en `AdminSettings.admin_notification_email` (futuro)
   - Fallback: primer usuario con `is_admin = true`

3. **Número de Orden**
   - Formato: `ORD-YYYYMM-####`
   - Ejemplo: `ORD-202512-0001`
   - Generado dinámicamente en cada correo

4. **Tracking URL Opcional**
   - Si no se proporciona, el correo no muestra botón de rastreo
   - Solo muestra número de guía

## 🔧 Futuras Mejoras

- [ ] Agregar campo `admin_notification_email` en AdminSettings
- [ ] Template para orden cancelada
- [ ] Template para orden refunded
- [x] ~~Soporte para adjuntar guía en PDF~~ ✅ Implementado
- [ ] Preview de correos en Storybook/React Email
- [ ] Logs de emails enviados en BD
- [ ] Reintentos automáticos si falla SMTP
- [ ] Soporte para múltiples archivos adjuntos
- [ ] Comprimir PDFs grandes automáticamente

## 📚 Recursos

- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [aiosmtplib](https://aiosmtplib.readthedocs.io/)
- [MailHog](https://github.com/mailhog/MailHog)
