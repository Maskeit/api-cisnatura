"""
Dependencias de autenticación para FastAPI.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from core.security import decode_token
from core.redis_service import TokenBlacklistService
from models.user import User
import uuid

# Security scheme para JWT
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Obtener el usuario actual desde el token JWT.
    
    Uso:
        @router.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    token = credentials.credentials
    
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Obtener el usuario actual si está autenticado, sino retornar None.
    
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
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_token(token)
        
        if not payload:
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
