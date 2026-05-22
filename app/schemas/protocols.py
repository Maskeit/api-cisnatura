"""
Schemas para Protocolos
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum



class ResourceType(str, Enum):
    IMAGE = "image"
    PDF = "pdf"
    VIDEO = "video"
    LINK = "link"
    DOWNLOAD = "download"


# ==================== PROTOCOL CATEGORY SCHEMAS ====================
class ProtocolCategoryBase(BaseModel):
    """Base para categorías de protocolos"""
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100)
    is_active: bool = True


class ProtocolCategoryCreate(ProtocolCategoryBase):
    """Crear categoría de protocolo"""
    pass


class ProtocolCategoryUpdate(BaseModel):
    """Actualizar categoría de protocolo"""
    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class ProtocolCategoryResponse(ProtocolCategoryBase):
    """Respuesta de categoría de protocolo"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== RESOURCE SCHEMAS ====================
class ProtocolResourceBase(BaseModel):
    """Base para recursos"""
    resource_type: ResourceType
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    url: str
    order: int = Field(..., ge=0)
    is_visible: bool = True


class ProtocolResourceCreate(ProtocolResourceBase):
    """Crear recurso"""
    pass


class ProtocolResourceResponse(ProtocolResourceBase):
    """Respuesta de recurso"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== PHASE SCHEMAS ====================
class ProtocolPhaseBase(BaseModel):
    """Base para fases"""
    title: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = None
    content: str  # HTML
    order: int = Field(..., ge=0)
    duration_minutes: Optional[int] = Field(None, ge=0)
    is_required: bool = True


class ProtocolPhaseCreate(ProtocolPhaseBase):
    """Crear fase con recursos opcionales"""
    resources: Optional[List[ProtocolResourceCreate]] = []


class ProtocolPhaseUpdate(BaseModel):
    """Actualizar fase"""
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_required: Optional[bool] = None
    order: Optional[int] = None


class ProtocolPhaseResponse(ProtocolPhaseBase):
    """Respuesta de fase"""
    id: int
    protocol_id: int
    resources: List[ProtocolResourceResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None  # onupdate: NULL hasta primer actualización
    
    class Config:
        from_attributes = True


# ==================== PROTOCOL SCHEMAS ====================
class ProtocolBase(BaseModel):
    """Base para protocolos"""
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100)
    description: str  # Breve
    long_description: Optional[str] = None
    price: float = Field(..., ge=0)  # Precio propio del protocolo
    image_url: Optional[str] = None
    author: Optional[str] = Field(None, max_length=255)
    category_id: int  # ID de la categoría del protocolo
    version: str = Field("1.0", max_length=50)
    estimated_duration_hours: Optional[int] = None    
    is_featured: bool = False


class ProtocolCreate(ProtocolBase):
    """Crear protocolo"""
    product_id: int  # Producto principal vinculado (para el carrito)
    associated_product_ids: Optional[List[int]] = []  # Productos relacionados/usados en el protocolo
    phases: Optional[List[ProtocolPhaseCreate]] = []
    
    @validator('slug')
    def validate_slug(cls, v):
        if not v or len(v) < 2:
            raise ValueError('Slug debe tener al menos 2 caracteres')
        return v


class ProtocolUpdate(BaseModel):
    """Actualizar protocolo"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    long_description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    image_url: Optional[str] = None
    author: Optional[str] = None
    category_id: Optional[int] = None
    version: Optional[str] = None
    estimated_duration_hours: Optional[int] = None    
    is_featured: Optional[bool] = None
    is_published: Optional[bool] = None
    associated_product_ids: Optional[List[int]] = None  # None = no cambiar


class ProtocolResponse(ProtocolBase):
    """Respuesta de protocolo"""
    id: int
    product_id: int
    is_published: bool
    category: ProtocolCategoryResponse  # Categoría completa
    phases: List[ProtocolPhaseResponse] = []
    associated_product_ids: List[int] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProtocolDetailedResponse(ProtocolResponse):
    """Protocolo con detalles completos para lectura"""
    total_phases: int = 0
    total_duration_hours: Optional[int] = None


# ==================== PROGRESS SCHEMAS ====================
class ProtocolProgressResponse(BaseModel):
    """Respuesta de progreso"""
    id: int
    protocol_id: int
    user_id: str
    current_phase_order: int
    completed_phases: int
    total_phases: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None  # NULL hasta primer acceso
    
    class Config:
        from_attributes = True


class ProtocolProgressUpdate(BaseModel):
    """Actualizar progreso"""
    current_phase_order: int = Field(..., ge=0)
    completed_phases: int = Field(..., ge=0)


# ==================== ACCESS SCHEMAS ====================
class ProtocolAccessResponse(BaseModel):
    """Respuesta de acceso"""
    id: int
    protocol_id: int
    user_id: str
    order_id: int
    order_item_id: int
    is_active: bool
    access_until: Optional[datetime]
    granted_at: datetime
    revoked_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ==================== LISTING SCHEMAS ====================
class ProtocolListItem(BaseModel):
    """Protocolo en listado"""
    id: int
    name: str
    slug: str
    description: str
    author: Optional[str]
    category: ProtocolCategoryResponse  # Categoría completa
    estimated_duration_hours: Optional[int]
    is_featured: bool
    total_phases: int = 0
    price: float = 0.0
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProtocolUserAccessResponse(BaseModel):
    """Protocolo que el usuario tiene acceso"""
    protocol_id: int
    protocol_name: str
    protocol_slug: str
    access_granted_at: datetime
    access_until: Optional[datetime]
    current_progress: Optional[ProtocolProgressResponse]
    
    class Config:
        from_attributes = True
