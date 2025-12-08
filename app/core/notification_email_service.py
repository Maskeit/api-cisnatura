"""
Servicio de notificaciones por correo para órdenes.
Emails informativos sin requerir acción del usuario.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from core.email_service import EmailService


class OrderNotificationService(EmailService):
    """
    Servicio para enviar notificaciones de órdenes a clientes y admins.
    Extiende EmailService para reutilizar configuración SMTP.
    """
    
    async def send_order_confirmation_to_customer(
        self,
        customer_email: str,
        customer_name: str,
        order_id: int,
        order_number: str,
        items: List[Dict],
        subtotal: Decimal,
        shipping_cost: Decimal,
        total: Decimal,
        shipping_address: Dict
    ) -> bool:
        """
        Enviar confirmación de pedido al cliente después del pago exitoso.
        
        Args:
            customer_email: Email del cliente
            customer_name: Nombre del cliente
            order_id: ID interno de la orden
            order_number: Número de orden visible (ej: "ORD-2025-001")
            items: Lista de productos [{name, quantity, price, subtotal}]
            subtotal: Subtotal sin envío
            shipping_cost: Costo de envío
            total: Total pagado
            shipping_address: {street, city, state, postal_code, country}
        
        Returns:
            bool: True si se envió correctamente
        """
        subject = f"✅ Confirmación de pedido #{order_number} - Cisnatura"
        
        # Construir lista de productos en HTML
        items_html = ""
        for item in items:
            items_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                    <strong>{item['name']}</strong><br>
                    <span style="color: #6b7280; font-size: 14px;">Cantidad: {item['quantity']}</span>
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    ${float(item['subtotal']):.2f} MXN
                </td>
            </tr>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Confirmación de Pedido</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">✅ ¡Pedido Confirmado!</h1>
            </div>
            
            <!-- Body -->
            <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <p style="font-size: 16px;">Hola <strong>{customer_name}</strong>,</p>
                
                <p style="font-size: 16px; color: #4b5563;">
                    ¡Gracias por tu compra! Hemos recibido tu pedido y el pago ha sido procesado exitosamente.
                    Te enviaremos tu guía de envío y número de rastreo pronto.
                </p>
                
                <!-- Order Number -->
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">Número de Pedido</p>
                    <p style="margin: 5px 0 0 0; font-size: 24px; font-weight: bold; color: #059669;">#{order_number}</p>
                </div>
                
                <!-- Order Items -->
                <h2 style="font-size: 18px; color: #1f2937; margin-top: 30px; margin-bottom: 15px;">
                    📦 Productos
                </h2>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                
                <!-- Order Summary -->
                <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <table style="width: 100%; font-size: 15px;">
                        <tr>
                            <td style="padding: 8px 0;">Subtotal:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 500;">${float(subtotal):.2f} MXN</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;">Envío:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 500;">
                                {'GRATIS' if float(shipping_cost) == 0 else f'${float(shipping_cost):.2f} MXN'}
                            </td>
                        </tr>
                        <tr style="border-top: 2px solid #e5e7eb;">
                            <td style="padding: 12px 0; font-size: 18px; font-weight: bold;">Total Pagado:</td>
                            <td style="padding: 12px 0; text-align: right; font-size: 18px; font-weight: bold; color: #059669;">
                                ${float(total):.2f} MXN
                            </td>
                        </tr>
                    </table>
                </div>
                
                <!-- Shipping Address -->
                <h2 style="font-size: 18px; color: #1f2937; margin-top: 30px; margin-bottom: 15px;">
                    🏠 Dirección de Envío
                </h2>
                <div style="background: #f9fafb; padding: 15px; border-radius: 8px; font-size: 15px; color: #4b5563;">
                    <p style="margin: 5px 0;">{shipping_address.get('street', '')}</p>
                    <p style="margin: 5px 0;">{shipping_address.get('city', '')}, {shipping_address.get('state', '')}</p>
                    <p style="margin: 5px 0;">C.P. {shipping_address.get('postal_code', '')}</p>
                    <p style="margin: 5px 0;">{shipping_address.get('country', 'México')}</p>
                </div>
                
                <!-- Next Steps -->
                <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 30px 0; border-radius: 4px;">
                    <p style="margin: 0; font-size: 14px; color: #1e40af;">
                        <strong>📬 Próximos pasos:</strong><br>
                        Procesaremos tu pedido y te enviaremos un correo con el número de rastreo cuando sea enviado.
                        Puedes revisar el estado de tu pedido en tu cuenta.
                    </p>
                </div>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{self.frontend_url}/perfil/mis-ordenes
                       style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                              color: white; 
                              padding: 14px 32px; 
                              text-decoration: none; 
                              border-radius: 6px; 
                              font-weight: 600;
                              display: inline-block;
                              font-size: 15px;">
                        Ver mis pedidos
                    </a>
                </div>
                
                <!-- Footer Note -->
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="font-size: 13px; color: #6b7280; text-align: center;">
                        Si tienes alguna pregunta sobre tu pedido, no dudes en contactarnos.
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 20px; color: #9ca3af; font-size: 12px;">
                <p>© 2025 Cisnatura. Todos los derechos reservados.</p>
                <p style="margin-top: 5px;">
                    Este es un correo de notificación, no es necesario responder.
                </p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
¡Pedido Confirmado!

Hola {customer_name},

Gracias por tu compra. Hemos recibido tu pedido y el pago ha sido procesado exitosamente.

Número de Pedido: #{order_number}

PRODUCTOS:
{chr(10).join([f"- {item['name']} (x{item['quantity']}): ${float(item['subtotal']):.2f} MXN" for item in items])}

RESUMEN:
Subtotal: ${float(subtotal):.2f} MXN
Envío: {'GRATIS' if float(shipping_cost) == 0 else f'${float(shipping_cost):.2f} MXN'}
Total Pagado: ${float(total):.2f} MXN

DIRECCIÓN DE ENVÍO:
{shipping_address.get('street', '')}
{shipping_address.get('city', '')}, {shipping_address.get('state', '')}
C.P. {shipping_address.get('postal_code', '')}
{shipping_address.get('country', 'México')}

Procesaremos tu pedido y te enviaremos un correo con el número de rastreo cuando sea enviado.

Ver mis pedidos: {self.frontend_url}/perfil/mis-ordenes

© 2025 Cisnatura
        """
        
        return await self.send_email(customer_email, subject, html_content, plain_content)
    
    async def send_new_order_notification_to_admin(
        self,
        admin_email: str,
        order_id: int,
        order_number: str,
        customer_name: str,
        customer_email: str,
        items_count: int,
        total: Decimal,
        payment_method: str = "Stripe"
    ) -> bool:
        """
        Notificar al admin sobre una nueva orden pagada.
        
        Args:
            admin_email: Email del administrador
            order_id: ID interno de la orden
            order_number: Número de orden visible
            customer_name: Nombre del cliente
            customer_email: Email del cliente
            items_count: Cantidad de productos
            total: Total de la orden
            payment_method: Método de pago usado
        
        Returns:
            bool: True si se envió correctamente
        """
        subject = f"🔔 Nueva Orden #{order_number} - ${float(total):.2f} MXN"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Nueva Orden</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">🔔 Nueva Orden Recibida</h1>
            </div>
            
            <!-- Body -->
            <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <p style="font-size: 16px;">
                    Se ha recibido una nueva orden pagada:
                </p>
                
                <!-- Order Highlight -->
                <div style="background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #1e40af; font-size: 14px;">Orden</p>
                    <p style="margin: 5px 0; font-size: 28px; font-weight: bold; color: #1e3a8a;">#{order_number}</p>
                    <p style="margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: #059669;">${float(total):.2f} MXN</p>
                </div>
                
                <!-- Order Details -->
                <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <table style="width: 100%; font-size: 15px;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Cliente:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600;">{customer_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Email:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 500;">{customer_email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Productos:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600;">{items_count} item(s)</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Método de Pago:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600;">{payment_method}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Estado:</td>
                            <td style="padding: 8px 0; text-align: right;">
                                <span style="background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 600;">
                                    ✓ PAGADA
                                </span>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <!-- Action Required -->
                <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; font-size: 14px; color: #92400e;">
                        <strong>⚠️ Acción requerida:</strong><br>
                        Prepara el pedido y actualiza el estado cuando esté listo para envío.
                    </p>
                </div>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{self.frontend_url}/admin/ordenes/{order_id}" 
                       style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
                              color: white; 
                              padding: 14px 32px; 
                              text-decoration: none; 
                              border-radius: 6px; 
                              font-weight: 600;
                              display: inline-block;
                              font-size: 15px;">
                        Ver Orden en Admin
                    </a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 20px; color: #9ca3af; font-size: 12px;">
                <p>© 2025 Cisnatura - Panel de Administración</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
🔔 Nueva Orden Recibida

Orden: #{order_number}
Total: ${float(total):.2f} MXN

DETALLES:
Cliente: {customer_name}
Email: {customer_email}
Productos: {items_count} item(s)
Método de Pago: {payment_method}
Estado: PAGADA

ACCIÓN REQUERIDA:
Prepara el pedido y actualiza el estado cuando esté listo para envío.

Ver orden: {self.frontend_url}/admin/orders/{order_id}

© 2025 Cisnatura
        """
        
        return await self.send_email(admin_email, subject, html_content, plain_content)
    
    async def send_shipping_notification_to_customer(
        self,
        customer_email: str,
        customer_name: str,
        order_number: str,
        tracking_number: str,
        shipping_carrier: str,
        tracking_url: Optional[str] = None,
        admin_notes: Optional[str] = None,
        pdf_attachment_path: Optional[str] = None
    ) -> bool:
        """
        Notificar al cliente que su pedido ha sido enviado.
        
        Args:
            customer_email: Email del cliente
            customer_name: Nombre del cliente
            order_number: Número de orden
            tracking_number: Número de guía/rastreo
            shipping_carrier: Paquetería (ej: "FedEx", "DHL", "Estafeta")
            tracking_url: URL de rastreo (opcional)
        
        Returns:
            bool: True si se envió correctamente
        """
        subject = f"📦 Tu pedido #{order_number} ha sido enviado"
        
        tracking_section = ""
        if tracking_url:
            tracking_section = f"""
            <div style="text-align: center; margin: 30px 0;">
                <a href="{tracking_url}" 
                   style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
                          color: white; 
                          padding: 14px 32px; 
                          text-decoration: none; 
                          border-radius: 6px; 
                          font-weight: 600;
                          display: inline-block;
                          font-size: 15px;">
                    🔍 Rastrear mi Pedido
                </a>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pedido Enviado</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">📦 ¡Tu Pedido Está en Camino!</h1>
            </div>
            
            <!-- Body -->
            <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <p style="font-size: 16px;">Hola <strong>{customer_name}</strong>,</p>
                
                <p style="font-size: 16px; color: #4b5563;">
                    ¡Buenas noticias! Tu pedido <strong>#{order_number}</strong> ha sido enviado y está en camino a tu dirección.
                </p>
                
                <!-- Tracking Info -->
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <table style="width: 100%; font-size: 15px;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Paquetería:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600;">{shipping_carrier}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Número de Guía:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #8b5cf6;">
                                {tracking_number}
                            </td>
                        </tr>
                    </table>
                </div>
                
                {tracking_section}
                
                <!-- Delivery Info -->
                <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; font-size: 14px; color: #92400e;">
                        <strong>📅 Tiempo de entrega estimado:</strong><br>
                        Tu pedido debería llegar en los próximos 3-5 días hábiles, dependiendo de tu ubicación.
                    </p>
                </div>
                
                <!-- Footer Note -->
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="font-size: 13px; color: #6b7280; text-align: center;">
                        Si tienes alguna pregunta o problema con tu entrega, contáctanos.
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 20px; color: #9ca3af; font-size: 12px;">
                <p>© 2025 Cisnatura. Todos los derechos reservados.</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
📦 ¡Tu Pedido Está en Camino!

Hola {customer_name},

Tu pedido #{order_number} ha sido enviado.

INFORMACIÓN DE ENVÍO:
Paquetería: {shipping_carrier}
Número de Guía: {tracking_number}

{f'Rastrear: {tracking_url}' if tracking_url else ''}

Tu pedido debería llegar en los próximos 3-5 días hábiles.

© 2025 Cisnatura
        """
        
        return await self.send_email(customer_email, subject, html_content, plain_content)


# Instancia global del servicio
notification_service = OrderNotificationService()
