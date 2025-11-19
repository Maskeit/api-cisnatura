"""
Schemas para direcciones de entrega.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional


# ==================== ADDRESS SCHEMAS ====================

class AddressBase(BaseModel):
    """Schema base para direcciones"""
    full_name: str = Field(..., min_length=2, max_length=255, description="Nombre completo del destinatario")
    phone: str = Field(..., min_length=10, max_length=20, description="Teléfono celular")
    rfc: Optional[str] = Field(None, description="RFC (opcional, 12-13 caracteres)")
    label: Optional[str] = Field(None, max_length=80, description="Etiqueta (Casa, Oficina, etc.)")
    street: str = Field(..., min_length=5, max_length=255, description="Calle y número")
    city: str = Field(..., min_length=2, max_length=120, description="Ciudad")
    state: str = Field(..., min_length=2, max_length=120, description="Estado/Provincia")
    postal_code: str = Field(..., min_length=3, max_length=10, description="Código postal")
    country: str = Field(..., min_length=2, max_length=80, description="País")
    is_default: bool = Field(False, description="¿Es la dirección predeterminada?")
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validar y limpiar teléfono"""
        # Eliminar espacios, guiones, paréntesis y caracteres especiales
        v = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        if not v.isdigit():
            raise ValueError('El teléfono solo puede contener números')
        if len(v) < 10:
            raise ValueError('El teléfono debe tener al menos 10 dígitos')
        return v
    
    @validator('rfc', pre=True)
    def validate_rfc(cls, v):
        """Validar RFC mexicano"""
        # Si es None, cadena vacía o solo espacios, retornar None
        if not v or (isinstance(v, str) and not v.strip()):
            return None
        
        # Validar formato
        v = v.strip().upper()
        if len(v) not in [12, 13]:
            raise ValueError('El RFC debe tener 12 o 13 caracteres')
        # Validación básica: primeros 4 letras, resto alfanumérico
        if not v[:4].isalpha() or not v[4:].isalnum():
            raise ValueError('Formato de RFC inválido')
        return v
    
    @validator('postal_code')
    def validate_postal_code(cls, v):
        """Validar formato de código postal"""
        # Eliminar espacios y guiones
        v = v.replace(' ', '').replace('-', '')
        if not v.isalnum():
            raise ValueError('El código postal solo puede contener letras y números')
        return v
    
    @validator('label')
    def validate_label(cls, v):
        """Capitalizar etiqueta"""
        if v:
            return v.strip().title()
        return v


class AddressCreate(AddressBase):
    """Schema para crear dirección"""
    pass


class AddressUpdate(BaseModel):
    """Schema para actualizar dirección (todos los campos opcionales)"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    rfc: Optional[str] = Field(None)
    label: Optional[str] = Field(None, max_length=80)
    street: Optional[str] = Field(None, min_length=5, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=120)
    state: Optional[str] = Field(None, min_length=2, max_length=120)
    postal_code: Optional[str] = Field(None, min_length=3, max_length=10)
    country: Optional[str] = Field(None, min_length=2, max_length=80)
    is_default: Optional[bool] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validar y limpiar teléfono"""
        if v:
            v = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
            if not v.isdigit():
                raise ValueError('El teléfono solo puede contener números')
            if len(v) < 10:
                raise ValueError('El teléfono debe tener al menos 10 dígitos')
        return v
    
    @validator('rfc', pre=True)
    def validate_rfc(cls, v):
        """Validar RFC mexicano"""
        # Si es None, cadena vacía o solo espacios, retornar None
        if not v or (isinstance(v, str) and not v.strip()):
            return None
        
        # Validar formato
        v = v.strip().upper()
        if len(v) not in [12, 13]:
            raise ValueError('El RFC debe tener 12 o 13 caracteres')
        if not v[:4].isalpha() or not v[4:].isalnum():
            raise ValueError('Formato de RFC inválido')
        return v
    
    @validator('postal_code')
    def validate_postal_code(cls, v):
        """Validar formato de código postal"""
        if v:
            v = v.replace(' ', '').replace('-', '')
            if not v.isalnum():
                raise ValueError('El código postal solo puede contener letras y números')
        return v
    
    @validator('label')
    def validate_label(cls, v):
        """Capitalizar etiqueta"""
        if v:
            return v.strip().title()
        return v


class AddressResponse(AddressBase):
    """Schema de respuesta con ID y fecha de creación"""
    id: int
    user_id: str
    created_at: str
    
    class Config:
        from_attributes = True


class AddressListResponse(BaseModel):
    """Lista de direcciones del usuario"""
    addresses: list[AddressResponse]
    total: int
    max_addresses: int = 3
