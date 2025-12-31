"""
Middleware y utilidades para protección CSRF.

CSRF (Cross-Site Request Forgery) aplica cuando:
- La API acepta cookies automáticamente para autenticación
- Las peticiones mutantes (POST, PUT, DELETE) deben verificar un token

Este módulo proporciona:
- Generación de tokens CSRF
- Middleware de validación CSRF
- Decoradores para proteger endpoints
"""
import secrets
import hmac
import hashlib
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Set
from core.config import settings


# Métodos HTTP que modifican datos y requieren protección CSRF
CSRF_PROTECTED_METHODS: Set[str] = {"POST", "PUT", "PATCH", "DELETE"}

# Rutas excluidas de protección CSRF (webhooks, APIs externas, etc.)
CSRF_EXEMPT_PATHS: Set[str] = {
    "/payments/webhook",  # Stripe webhook
    "/payments/stripe/webhook",
    "/auth/google-login",  # Firebase token se valida de otra forma
}

# Header donde el frontend envía el token CSRF
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    """
    Generar un token CSRF criptográficamente seguro.
    
    Returns:
        Token CSRF de 32 bytes en formato hexadecimal
    """
    return secrets.token_hex(32)


def validate_csrf_token(cookie_token: Optional[str], header_token: Optional[str]) -> bool:
    """
    Validar que el token CSRF del header coincida con el de la cookie.
    
    Usamos comparación de tiempo constante para prevenir timing attacks.
    
    Args:
        cookie_token: Token almacenado en la cookie
        header_token: Token enviado en el header por el frontend
        
    Returns:
        True si los tokens son válidos y coinciden
    """
    if not cookie_token or not header_token:
        return False
    
    # Comparación de tiempo constante
    return hmac.compare_digest(cookie_token, header_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware para protección CSRF.
    
    Funciona así:
    1. En el login, se genera un token CSRF y se envía en una cookie
    2. El frontend lee esa cookie y la envía en el header X-CSRF-Token
    3. Este middleware valida que ambos coincidan
    
    Solo aplica cuando:
    - El usuario está autenticado via cookies (no Bearer token en header)
    - El método HTTP es mutante (POST, PUT, PATCH, DELETE)
    """
    
    async def dispatch(self, request: Request, call_next):
        # Solo verificar CSRF para métodos que modifican datos
        if request.method not in CSRF_PROTECTED_METHODS:
            return await call_next(request)
        
        # Verificar si la ruta está exenta
        path = request.url.path
        if any(path.startswith(exempt) for exempt in CSRF_EXEMPT_PATHS):
            return await call_next(request)
        
        # Si usa Bearer token en header, no necesita CSRF
        # (el token en header ya prueba que es una request legítima)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)
        
        # Si tiene cookie de sesión, verificar CSRF
        access_token_cookie = request.cookies.get("access_token")
        
        if access_token_cookie:
            # Usuario autenticado via cookie - CSRF requerido
            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get(CSRF_HEADER_NAME)
            
            if not validate_csrf_token(csrf_cookie, csrf_header):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "success": False,
                        "status_code": 403,
                        "message": "Token CSRF inválido o faltante",
                        "error": "CSRF_VALIDATION_FAILED"
                    }
                )
        
        return await call_next(request)


def get_csrf_exempt_paths() -> Set[str]:
    """
    Obtener rutas exentas de protección CSRF.
    
    Returns:
        Set de rutas exentas
    """
    return CSRF_EXEMPT_PATHS.copy()


def add_csrf_exempt_path(path: str) -> None:
    """
    Agregar una ruta a la lista de exentas de CSRF.
    
    Args:
        path: Ruta a agregar (ej: "/api/external-webhook")
    """
    CSRF_EXEMPT_PATHS.add(path)
