"""
Schemas para notificaciones de órdenes por correo.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class ShippingNotificationRequest(BaseModel):
    """
    Schema para enviar notificación de envío al cliente.
    Usado por el admin cuando marca una orden como enviada.
    """
    order_id: int = Field(..., description="ID de la orden a notificar")
    tracking_number: str = Field(..., min_length=1, max_length=100, description="Número de guía/rastreo")
    shipping_carrier: str = Field(..., min_length=1, max_length=50, description="Nombre de la paquetería (FedEx, DHL, Estafeta, etc.)")
    tracking_url: Optional[str] = Field(None, description="URL de rastreo de la paquetería (opcional)")
    admin_notes: Optional[str] = Field(None, description="Notas internas opcionales para adjuntar al correo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 123,
                "tracking_number": "1234567890",
                "shipping_carrier": "FedEx",
                "tracking_url": "https://www.fedex.com/apps/fedextrack/?tracknumbers=1234567890",
                "admin_notes": "Su paquete llegará en 3-5 días hábiles"
            }
        }


class NotificationResponse(BaseModel):
    """
    Respuesta estándar para operaciones de notificación.
    """
    success: bool
    message: str
    email_sent: bool
    recipient: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Notificación de envío enviada correctamente",
                "email_sent": True,
                "recipient": "cliente@example.com"
            }
        }
