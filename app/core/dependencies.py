"""
Dependencias de autenticación para FastAPI.

Soporta dos métodos de autenticación:
1. Bearer Token (Authorization header) - API tradicional
2. HttpOnly Cookies - Más seguro para SPAs (protegido contra XSS)

El sistema intenta primero leer de cookies HttpOnly, 
luego fallback a Bearer token para compatibilidad.
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from core.security import decode_token
from core.redis_service import TokenBlacklistService
from core.cookie_auth import get_access_token_from_request
from models.user import User
import uuid


# Security scheme personalizado para JWT con mensajes de error consistentes
class CustomHTTPBearer(HTTPBearer):
    """
    Bearer scheme que NO falla si no hay token.
    La verificación real se hace en get_current_user que también revisa cookies.
    """
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        try:
            return await super().__call__(request)
        except HTTPException:
            # No lanzar error aquí - permitir que get_current_user revise cookies
            return None


security = CustomHTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Obtener el usuario actual desde cookies HttpOnly o Bearer token.
    
    Prioridad de autenticación:
    1. Cookie HttpOnly 'access_token' (más seguro, recomendado para SPAs)
    2. Header 'Authorization: Bearer <token>' (compatibilidad con APIs)
    
    Uso:
        @router.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    # Intentar obtener token de cookies HttpOnly primero, luego de Bearer header
    token = get_access_token_from_request(request)
    
    # Fallback: si no hay token en cookies, usar el del Bearer header
    if not token and credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Token de autenticación requerido",
                "error": "AUTHENTICATION_REQUIRED"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Decodificar token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Token inválido o expirado",
                "error": "INVALID_TOKEN"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verificar si el token está revocado (logout)
    token_jti = payload.get("jti")
    if token_jti and TokenBlacklistService.is_token_revoked(token_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Token revocado. Por favor, inicia sesión nuevamente.",
                "error": "TOKEN_REVOKED"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Obtener ID del usuario
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Token inválido",
                "error": "INVALID_TOKEN"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Token inválido",
                "error": "INVALID_TOKEN"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Buscar usuario en la base de datos
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Usuario no encontrado",
                "error": "USER_NOT_FOUND"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verificar que el usuario esté activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "status_code": 403,
                "message": "Usuario inactivo",
                "error": "USER_INACTIVE"
            }
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Obtener usuario actual y verificar que esté activo.
    (Esta función es redundante ya que get_current_user ya verifica is_active,
    pero se mantiene por compatibilidad)
    """
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verificar que el usuario autenticado sea administrador.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "status_code": 403,
                "message": "No tienes permisos de administrador",
                "error": "ADMIN_REQUIRED"
            }
        )
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Obtener el usuario actual si está autenticado, sino retornar None.
    
    Soporta cookies HttpOnly y Bearer token.
    
    Útil para endpoints públicos que cambian su comportamiento si el usuario está autenticado.
    
    Uso:
        @router.get("/products")
        async def list_products(
            current_user: Optional[User] = Depends(get_optional_current_user)
        ):
            # current_user puede ser None si no está autenticado
            if current_user:
                # Mostrar precios con descuento para usuarios registrados
                pass
            else:
                # Mostrar precios normales
                pass
    """
    # Intentar obtener token de cookies primero
    token = get_access_token_from_request(request)
    
    # Fallback a Bearer header
    if not token and credentials:
        token = credentials.credentials
    
    if not token:
        return None
    
    try:
        payload = decode_token(token)
        
        if not payload:
            return None
        
        # Verificar si el token está revocado
        token_jti = payload.get("jti")
        if token_jti and TokenBlacklistService.is_token_revoked(token_jti):
            return None
        
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        
        user_id = uuid.UUID(user_id_str)
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        return user
        
    except Exception:
        return None
