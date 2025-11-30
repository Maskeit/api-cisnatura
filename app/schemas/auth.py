"""
Schemas de autenticación y usuarios.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import uuid


# ==================== AUTH SCHEMAS ====================

class UserRegister(BaseModel):
    """Schema para registro de usuario"""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, max_length=100, description="Contraseña (mínimo 8 caracteres)")
    full_name: str = Field(..., min_length=2, max_length=255, description="Nombre completo")
    
    @validator('password')
    def validate_password(cls, v):
        """Validar que la contraseña sea fuerte"""
        if not any(char.isdigit() for char in v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not any(char.isupper() for char in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(char.islower() for char in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        return v


class UserLogin(BaseModel):
    """Schema para login de usuario"""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., description="Contraseña")


class TokenResponse(BaseModel):
    """Schema para respuesta de token"""
    access_token: str = Field(..., description="Token de acceso JWT")
    refresh_token: str = Field(..., description="Token de refresh JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Segundos hasta la expiración")


class RefreshTokenRequest(BaseModel):
    """Schema para solicitud de refresh token"""
    refresh_token: str = Field(..., description="Token de refresh")


class VerifyEmailRequest(BaseModel):
    """Schema para verificación de email"""
    token: str = Field(..., description="Token de verificación de email")


class ResendVerificationRequest(BaseModel):
    """Schema para reenvío de email de verificación"""
    email: EmailStr = Field(..., description="Email del usuario")


class ForgotPasswordRequest(BaseModel):
    """Schema para solicitud de recuperación de contraseña"""
    email: EmailStr = Field(..., description="Email del usuario")


class ResetPasswordRequest(BaseModel):
    """Schema para resetear contraseña"""
    token: str = Field(..., description="Token de recuperación")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nueva contraseña")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validar que la contraseña sea fuerte"""
        if not any(char.isdigit() for char in v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not any(char.isupper() for char in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(char.islower() for char in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        return v


# ==================== USER SCHEMAS ====================

class UserBase(BaseModel):
    """Schema base de usuario"""
    email: EmailStr
    full_name: str


class UserResponse(UserBase):
    """Schema de respuesta de usuario"""
    id: uuid.UUID
    is_active: bool
    is_admin: bool
    email_verified: bool
    email_verified_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    """Schema para cambio de contraseña"""
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nueva contraseña")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validar que la contraseña sea fuerte"""
        if not any(char.isdigit() for char in v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not any(char.isupper() for char in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(char.islower() for char in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        return v


# ==================== GOOGLE AUTH SCHEMAS ====================

class GoogleLoginRequest(BaseModel):
    """Schema para login con Google"""
    firebase_token: str = Field(..., description="Token de ID de Firebase")


class GoogleAuthResponse(BaseModel):
    """Schema para respuesta de autenticación con Google"""
    access_token: str = Field(..., description="Token de acceso JWT")
    refresh_token: str = Field(..., description="Token de refresh JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Segundos hasta la expiración")
    user: dict = Field(..., description="Información del usuario")
    is_new_user: bool = Field(..., description="Indica si el usuario es nuevo")
