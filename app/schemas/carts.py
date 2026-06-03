"""
Schemas para carritos de compra.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


class CartItemType(str, Enum):
    PRODUCT = "product"
    PROTOCOL = "protocol"


# ==================== CART ITEM SCHEMAS ====================

class CartItemBase(BaseModel):
    """Schema base para items del carrito"""
    product_id: int = Field(..., description="ID del producto")
    quantity: int = Field(..., ge=1, le=100, description="Cantidad (1-100)")


class CartItemCreate(BaseModel):
    """Agregar un item al carrito (producto o protocolo).

    - Productos (físicos): { "product_id": N, "quantity": Q }  (item_type por defecto)
    - Protocolos (digitales): { "item_type": "protocol", "protocol_id": N }
    """
    item_type: CartItemType = CartItemType.PRODUCT
    product_id: Optional[int] = Field(None, description="ID del producto (item_type=product)")
    protocol_id: Optional[int] = Field(None, description="ID del protocolo (item_type=protocol)")
    quantity: int = Field(1, ge=1, le=100, description="Cantidad (1-100)")

    @validator("protocol_id", always=True)
    def validate_target_id(cls, protocol_id, values):
        item_type = values.get("item_type")
        product_id = values.get("product_id")
        if item_type == CartItemType.PROTOCOL:
            if not protocol_id:
                raise ValueError("protocol_id es requerido cuando item_type='protocol'")
        else:
            if not product_id:
                raise ValueError("product_id es requerido cuando item_type='product'")
        return protocol_id

    @property
    def item_id(self) -> int:
        """ID del item según su tipo."""
        return self.protocol_id if self.item_type == CartItemType.PROTOCOL else self.product_id


class CartItemUpdate(BaseModel):
    """Schema para actualizar cantidad de un item"""
    quantity: int = Field(..., ge=1, le=100, description="Nueva cantidad (1-100)")


class CartItemProduct(BaseModel):
    """Información del producto en el carrito"""
    id: int
    name: str
    slug: str
    price: float
    stock: int
    image_url: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class CartItemResponse(BaseModel):
    """Item del carrito con información del producto"""
    id: int
    cart_id: int
    product_id: int
    quantity: int
    product: CartItemProduct
    subtotal: float  # price * quantity
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


# ==================== CART SCHEMAS ====================

class CartResponse(BaseModel):
    """Carrito completo con sus items"""
    id: int
    user_id: str
    is_active: bool
    items: List[CartItemResponse]
    total_items: int  # Cantidad total de productos
    total_amount: float  # Suma de todos los subtotales
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class CartSummary(BaseModel):
    """Resumen del carrito (para badges, etc.)"""
    total_items: int
    total_amount: float
