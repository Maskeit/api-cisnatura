"""
Schemas para productos y categorías.
"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


# ==================== CATEGORY SCHEMAS ====================

class CategoryBase(BaseModel):
    """Schema base para categorías"""
    name: str = Field(..., min_length=2, max_length=100, description="Nombre de la categoría")
    slug: str = Field(..., min_length=2, max_length=100, description="Slug URL-friendly")
    description: Optional[str] = Field(None, max_length=500, description="Descripción de la categoría")
    image_url: Optional[str] = Field(None, description="URL de la imagen")


class CategoryCreate(CategoryBase):
    """Schema para crear categoría"""
    pass


class CategoryUpdate(BaseModel):
    """Schema para actualizar categoría"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    """Schema de respuesta para categoría"""
    id: int
    is_active: bool
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


# ==================== PRODUCT SCHEMAS ====================

class ProductBase(BaseModel):
    """Schema base para productos"""
    name: str = Field(..., min_length=2, max_length=200, description="Nombre del producto")
    slug: str = Field(..., min_length=2, max_length=200, description="Slug URL-friendly")
    description: str = Field(..., min_length=10, description="Descripción del producto")
    price: float = Field(..., gt=0, description="Precio del producto (debe ser mayor a 0)")
    stock: int = Field(..., ge=0, description="Stock disponible (no puede ser negativo)")
    category_id: int = Field(..., description="ID de la categoría")
    image_url: Optional[str] = Field(None, description="URL de la imagen")


class ProductCreate(ProductBase):
    """Schema para crear producto"""
    pass


class ProductUpdate(BaseModel):
    """Schema para actualizar producto"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    slug: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schema de respuesta para producto"""
    id: int
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True