from sqlalchemy import Column, String, Boolean, Float, JSON, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from core.database import Base


class AdminSettings(Base):
    """
    Tabla de configuraciones administrativas del sistema.
    Solo debe existir UN registro en esta tabla.
    """
    __tablename__ = "admin_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Control de mantenimiento - Bloquea API para usuarios normales
    maintenance_mode = Column(Boolean, default=False, nullable=False)
    maintenance_message = Column(String(500), default="Sistema en mantenimiento. Intente más tarde.")
    
    # Precio de envío (en la moneda que uses, ej: USD, MXN, etc)
    shipping_price = Column(Float, default=0.0, nullable=False)
    free_shipping_threshold = Column(Float, default=None, nullable=True)  # Envío gratis si compra supera este monto
    categories_no_shipping = Column(JSON, default=[], nullable=False)  # IDs de categorías que no pagan envío (productos digitales)
    
    # Descuento global (porcentaje 0-100)
    global_discount_enabled = Column(Boolean, default=False, nullable=False)
    global_discount_percentage = Column(Float, default=0.0, nullable=False)
    global_discount_name = Column(String(100), default="Oferta Especial")
    
    # Descuentos por categoría - JSON: {"category_id": {"percentage": 10, "name": "Black Friday"}}
    category_discounts = Column(JSON, default={}, nullable=False)
    
    # Descuentos por producto específico - JSON: {"product_id": {"percentage": 15, "name": "Liquidación"}}
    product_discounts = Column(JSON, default={}, nullable=False)
    
    # Temporadas/Ofertas especiales - JSON array de objetos con fechas
    # [{"name": "Black Friday", "start": "2024-11-24", "end": "2024-11-30", "discount": 20, "categories": [...]}]
    seasonal_offers = Column(JSON, default=[], nullable=False)
    
    # Control de registro de usuarios
    allow_user_registration = Column(Boolean, default=True, nullable=False)
    
    # Límite de productos por orden
    max_items_per_order = Column(Integer, default=50, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<AdminSettings(maintenance={self.maintenance_mode}, shipping={self.shipping_price})>"
