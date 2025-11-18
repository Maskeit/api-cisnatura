"""
Schemas para carritos de compra.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


# ==================== CART ITEM SCHEMAS ====================

class CartItemBase(BaseModel):
    """Schema base para items del carrito"""
    product_id: int = Field(..., description="ID del producto")
    quantity: int = Field(..., ge=1, le=100, description="Cantidad (1-100)")


class CartItemCreate(CartItemBase):
    """Schema para agregar producto al carrito"""
    pass


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
