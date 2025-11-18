"""
Utilidades para seguridad: contraseñas y JWT
"""
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from core.config import settings


# ==================== PASSWORD HASHING ====================

def hash_password(password: str) -> str:
    """
    Hash password usando bcrypt.
    Genera un hash de 60 caracteres.
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar si una contraseña coincide con su hash.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# ==================== JWT TOKEN MANAGEMENT ====================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Crear un token JWT de acceso.
    
    Args:
        data: Datos a incluir en el token (payload)
        expires_delta: Tiempo de expiración personalizado (opcional)
    
    Returns:
        str: Token JWT codificado
    """
    import uuid
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": str(uuid.uuid4())  # JWT ID único para identificar el token
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Crear un token JWT de refresh (larga duración).
    
    Args:
        data: Datos a incluir en el token (payload)
    
    Returns:
        str: Token JWT codificado
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodificar y validar un token JWT.
    
    Args:
        token: Token JWT a decodificar
    
    Returns:
        Dict con el payload del token o None si es inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verificar que el token es del tipo esperado (access o refresh).
    
    Args:
        token: Token JWT
        expected_type: Tipo esperado ("access" o "refresh")
    
    Returns:
        bool: True si el tipo coincide
    """
    payload = decode_token(token)
    if not payload:
        return False
    
    return payload.get("type") == expected_type
