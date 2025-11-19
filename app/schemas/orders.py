"""
Schemas para órdenes de compra.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ==================== ENUMS ====================

class OrderStatus(str):
    PENDING = "pending"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    MERCADOPAGO = "mercadopago"
    OPENPAY = "openpay"
    CASH = "cash"
    TRANSFER = "transfer"


# ==================== ORDER ITEM SCHEMAS ====================

class OrderItemBase(BaseModel):
    """Schema base para item de orden"""
    product_id: int
    quantity: int = Field(..., gt=0, description="Cantidad del producto")


class OrderItemResponse(BaseModel):
    """Respuesta de item de orden"""
    id: int
    product_id: int
    product_name: str
    product_sku: Optional[str]
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    
    class Config:
        from_attributes = True


# ==================== ORDER SCHEMAS ====================

class OrderCreate(BaseModel):
    """Crear orden desde el carrito"""
    address_id: int = Field(..., description="ID de la dirección de envío")
    payment_method: str = Field(default="stripe", description="Método de pago")
    notes: Optional[str] = Field(None, max_length=500, description="Notas del cliente")
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        """Validar método de pago"""
        valid_methods = ["stripe", "paypal", "mercadopago", "openpay"]
        if v not in valid_methods:
            raise ValueError(f"Método de pago debe ser uno de: {', '.join(valid_methods)}")
        return v


class OrderResponse(BaseModel):
    """Respuesta completa de orden"""
    id: int
    user_id: str
    address_id: int
    
    # Información de pago
    payment_method: str
    payment_id: Optional[str]
    payment_status: Optional[str]
    
    # Estado y montos
    status: str
    subtotal: Decimal
    shipping_cost: Decimal
    tax: Decimal
    total: Decimal
    
    # Datos adicionales
    notes: Optional[str]
    tracking_number: Optional[str]
    
    # Items
    order_items: List[OrderItemResponse]
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    paid_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    """Item de lista de órdenes (sin items detallados)"""
    id: int
    status: str
    payment_method: str
    total: Decimal
    items_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== ADMIN SCHEMAS ====================

class OrderStatusUpdate(BaseModel):
    """Actualizar estado de orden (admin)"""
    status: str = Field(..., description="Nuevo estado de la orden")
    admin_notes: Optional[str] = Field(None, max_length=500, description="Notas internas")
    tracking_number: Optional[str] = Field(None, max_length=255, description="Número de guía")
    
    @validator('status')
    def validate_status(cls, v):
        """Validar estado"""
        valid_statuses = [
            "pending", "payment_pending", "paid", "processing", 
            "shipped", "delivered", "cancelled", "refunded"
        ]
        if v not in valid_statuses:
            raise ValueError(f"Estado debe ser uno de: {', '.join(valid_statuses)}")
        return v


class OrderAdminResponse(OrderResponse):
    """Respuesta de orden para admin (incluye notas internas)"""
    admin_notes: Optional[str]
    
    # Información de dirección completa
    shipping_address: Optional[dict]
    
    # Información de usuario
    user_email: Optional[str]
    user_name: Optional[str]


class OrderStatsResponse(BaseModel):
    """Estadísticas de órdenes"""
    total_orders: int
    total_revenue: Decimal
    pending_orders: int
    processing_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int
    
    # Ganancias por período
    revenue_today: Decimal
    revenue_this_week: Decimal
    revenue_this_month: Decimal
    revenue_this_year: Decimal
    
    # Top productos (opcional)
    top_products: Optional[List[dict]]


class OrderFilters(BaseModel):
    """Filtros para listar órdenes (admin)"""
    status: Optional[str] = None
    payment_method: Optional[str] = None
    user_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_total: Optional[Decimal] = None
    max_total: Optional[Decimal] = None
