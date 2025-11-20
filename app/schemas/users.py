"""
Schema de usuarios
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ==================== USER SCHEMAS ====================
class UserBase(BaseModel):
    """Schema base de usuario"""
    email: EmailStr
    full_name: str


class UserProfileResponse(BaseModel):
    """Respuesta de perfil de usuario"""
    id: str
    email: str
    full_name: str
    is_active: bool
    is_admin: bool
    email_verified: bool
    email_verified_at: Optional[datetime]
    created_at: datetime
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        """Convertir UUID a string"""
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class UserUpdateProfile(BaseModel):
    """Actualizar perfil de usuario"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Nombre completo")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validar y limpiar nombre"""
        if v:
            v = v.strip()
            if len(v) < 2:
                raise ValueError('El nombre debe tener al menos 2 caracteres')
        return v


class UserChangePassword(BaseModel):
    """Cambiar contraseña de usuario"""
    current_password: str = Field(..., min_length=8, description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    confirm_password: str = Field(..., min_length=8, description="Confirmar nueva contraseña")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validar que las contraseñas coincidan"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v, values):
        """Validar que la nueva contraseña sea diferente"""
        if 'current_password' in values and v == values['current_password']:
            raise ValueError('La nueva contraseña debe ser diferente a la actual')
        return v


class UserProfileSummary(BaseModel):
    """Resumen del perfil con estadísticas"""
    profile: UserProfileResponse
    
    # Estadísticas de órdenes
    total_orders: int
    completed_orders: int
    pending_orders: int
    total_spent: Decimal
    
    # Resumen de direcciones
    total_addresses: int
    has_default_address: bool
    
    # Última orden
    last_order: Optional[dict]
    
    class Config:
        from_attributes = True


# ==================== ADMIN USER MANAGEMENT SCHEMAS ====================

class UserAdminResponse(UserProfileResponse):
    """Respuesta de usuario para admin (más detalles)"""
    updated_at: Optional[datetime]
    
    # Estadísticas adicionales
    total_orders: Optional[int] = 0
    total_spent: Optional[Decimal] = Decimal('0')
    total_addresses: Optional[int] = 0
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        """Convertir UUID a string"""
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class UserAdminUpdate(BaseModel):
    """Actualizar usuario (solo admin)"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    is_active: Optional[bool] = Field(None, description="Activar/desactivar usuario")
    is_admin: Optional[bool] = Field(None, description="Otorgar/quitar permisos de admin")
    email_verified: Optional[bool] = Field(None, description="Marcar email como verificado")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validar y limpiar nombre"""
        if v:
            v = v.strip()
            if len(v) < 2:
                raise ValueError('El nombre debe tener al menos 2 caracteres')
        return v


class UserAdminFilters(BaseModel):
    """Filtros para buscar usuarios (admin)"""
    search: Optional[str] = Field(None, description="Buscar por email o nombre")
    is_active: Optional[bool] = Field(None, description="Filtrar por estado activo")
    is_admin: Optional[bool] = Field(None, description="Filtrar por rol admin")
    email_verified: Optional[bool] = Field(None, description="Filtrar por email verificado")
    created_from: Optional[datetime] = Field(None, description="Fecha de registro desde")
    created_to: Optional[datetime] = Field(None, description="Fecha de registro hasta")
    min_orders: Optional[int] = Field(None, ge=0, description="Mínimo de órdenes")
    min_spent: Optional[Decimal] = Field(None, ge=0, description="Mínimo gastado")


class UserAdminStats(BaseModel):
    """Estadísticas generales de usuarios (admin)"""
    total_users: int
    active_users: int
    inactive_users: int
    admin_users: int
    verified_users: int
    unverified_users: int
    
    # Estadísticas de registro
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    
    # Top usuarios
    top_spenders: Optional[List[dict]]


class UserBanRequest(BaseModel):
    """Banear/desbanear usuario"""
    reason: Optional[str] = Field(None, max_length=500, description="Razón del baneo")