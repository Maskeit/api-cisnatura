from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime


class SeasonalOffer(BaseModel):
    """Oferta temporal/estacional"""
    name: str = Field(..., description="Nombre de la oferta (ej: Black Friday)")
    start_date: str = Field(..., description="Fecha inicio (YYYY-MM-DD)")
    end_date: str = Field(..., description="Fecha fin (YYYY-MM-DD)")
    discount_percentage: float = Field(..., ge=0, le=100, description="Porcentaje de descuento")
    category_ids: Optional[List[str]] = Field(default=None, description="IDs de categorías (null = todas)")
    product_ids: Optional[List[str]] = Field(default=None, description="IDs de productos específicos")
    
    @validator('discount_percentage')
    def validate_discount(cls, v):
        if v < 0 or v > 100:
            raise ValueError('El descuento debe estar entre 0 y 100')
        return v


class CategoryDiscount(BaseModel):
    """Descuento por categoría"""
    category_id: str
    percentage: float = Field(..., ge=0, le=100)
    name: str = Field(..., max_length=100)


class ProductDiscount(BaseModel):
    """Descuento por producto"""
    product_id: str
    percentage: float = Field(..., ge=0, le=100)
    name: str = Field(..., max_length=100)


class AdminSettingsResponse(BaseModel):
    """Respuesta con todas las configuraciones"""
    id: str
    
    # Maintenance
    maintenance_mode: bool
    maintenance_message: str
    
    # Shipping
    shipping_price: float
    free_shipping_threshold: Optional[float]
    
    # Global discount
    global_discount_enabled: bool
    global_discount_percentage: float
    global_discount_name: str
    
    # Discounts
    category_discounts: Dict
    product_discounts: Dict
    seasonal_offers: List
    
    # Other settings
    allow_user_registration: bool
    max_items_per_order: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            # Convertir UUID a string automáticamente
            'UUID': str
        }
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        """Convertir UUID a string"""
        if hasattr(v, 'hex'):  # Es un UUID
            return str(v)
        return v


class UpdateMaintenanceMode(BaseModel):
    """Activar/desactivar modo mantenimiento"""
    maintenance_mode: bool
    maintenance_message: Optional[str] = Field(None, max_length=500)


class UpdateShippingPrice(BaseModel):
    """Actualizar precio de envío"""
    shipping_price: float = Field(..., ge=0, description="Precio de envío")
    free_shipping_threshold: Optional[float] = Field(None, ge=0, description="Compra mínima para envío gratis")


class UpdateGlobalDiscount(BaseModel):
    """Actualizar descuento global"""
    enabled: bool
    percentage: float = Field(..., ge=0, le=100)
    name: str = Field(..., max_length=100)


class AddCategoryDiscount(BaseModel):
    """Agregar descuento a una categoría"""
    category_id: str
    percentage: float = Field(..., ge=0, le=100)
    name: str = Field(..., max_length=100, description="Nombre de la oferta")


class AddProductDiscount(BaseModel):
    """Agregar descuento a un producto"""
    product_id: str
    percentage: float = Field(..., ge=0, le=100)
    name: str = Field(..., max_length=100, description="Nombre de la oferta")


class AddSeasonalOffer(BaseModel):
    """Crear oferta temporal"""
    name: str = Field(..., max_length=100)
    start_date: str = Field(..., description="Formato: YYYY-MM-DD")
    end_date: str = Field(..., description="Formato: YYYY-MM-DD")
    discount_percentage: float = Field(..., ge=0, le=100)
    category_ids: Optional[List[str]] = Field(default=None, description="null = todas las categorías")
    product_ids: Optional[List[str]] = Field(default=None, description="Productos específicos")
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Formato de fecha inválido. Use YYYY-MM-DD')
        return v


class UpdateUserRegistration(BaseModel):
    """Activar/desactivar registro de usuarios"""
    allow_user_registration: bool


class UpdateMaxItemsPerOrder(BaseModel):
    """Actualizar límite de productos por orden"""
    max_items_per_order: int = Field(..., ge=1, le=1000)


class DiscountInfo(BaseModel):
    """Información de descuento aplicado a un producto"""
    original_price: float
    discounted_price: float
    discount_percentage: float
    discount_name: str
    is_active: bool


# Respuestas específicas para cada endpoint
class MaintenanceResponse(BaseModel):
    """Respuesta al actualizar modo mantenimiento"""
    success: bool = True
    status_code: int = 200
    message: str
    data: Dict = Field(..., description="maintenance_mode y maintenance_message")


class ShippingResponse(BaseModel):
    """Respuesta al actualizar precio de envío"""
    success: bool = True
    status_code: int = 200
    message: str
    data: Dict = Field(..., description="shipping_price y free_shipping_threshold")


class GlobalDiscountResponse(BaseModel):
    """Respuesta al actualizar descuento global"""
    success: bool = True
    status_code: int = 200
    message: str
    data: Dict = Field(..., description="enabled, percentage, name")


class CategoryDiscountResponse(BaseModel):
    """Respuesta al agregar/eliminar descuento de categoría"""
    success: bool = True
    status_code: int = 200
    message: str
    data: Dict = Field(..., description="category_discounts")


class ProductDiscountResponse(BaseModel):
    """Respuesta al agregar/eliminar descuento de producto"""
    success: bool = True
    status_code: int = 200
    message: str
    data: Dict = Field(..., description="product_discounts")


class SeasonalOfferResponse(BaseModel):
    """Respuesta al agregar/eliminar oferta temporal"""
    success: bool = True
    status_code: int = 200
    message: str
    data: List = Field(..., description="seasonal_offers")
