from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import enum

# Estados de la orden
class OrderStatus(str, enum.Enum):
    PENDING = "pending"              # Orden creada, esperando pago
    PAYMENT_PENDING = "payment_pending"  # Pago en proceso
    PAID = "paid"                    # Pagada, esperando procesamiento
    PROCESSING = "processing"        # En preparación
    SHIPPED = "shipped"              # Enviada
    DELIVERED = "delivered"          # Entregada
    CANCELLED = "cancelled"          # Cancelada
    REFUNDED = "refunded"            # Reembolsada

# Métodos de pago
class PaymentMethod(str, enum.Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    OPENPAY = "openpay"
    CASH = "cash"                    # Para admin
    TRANSFER = "transfer"            # Para admin

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    address_id = Column(Integer, ForeignKey("addresses.id"), nullable=False, index=True)
    
    # Información de pago
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False, default=PaymentMethod.STRIPE)
    payment_id = Column(String(255), nullable=True, index=True)  # ID de la pasarela de pago
    payment_status = Column(String(50), nullable=True)  # Estado específico de la pasarela
    
    # Estado y montos
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    shipping_cost = Column(Numeric(10, 2), nullable=False, default=0)
    tax = Column(Numeric(10, 2), nullable=False, default=0)
    total = Column(Numeric(10, 2), nullable=False)
    
    # Datos adicionales
    notes = Column(Text, nullable=True)  # Notas del cliente
    admin_notes = Column(Text, nullable=True)  # Notas internas
    tracking_number = Column(String(255), nullable=True)  # Número de guía
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="orders")
    address = relationship("Address", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # Snapshot del producto al momento de la compra
    product_name = Column(String(255), nullable=False)  # Nombre del producto
    product_sku = Column(String(100), nullable=True)    # SKU
    
    # Cantidades y precios
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)  # Precio unitario al momento de la compra
    subtotal = Column(Numeric(10, 2), nullable=False)    # quantity * unit_price
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    cart = relationship("Cart", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")