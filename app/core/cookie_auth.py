"""
Módulo de autenticación segura mediante cookies HttpOnly.

Este módulo proporciona funciones para manejar cookies de sesión
de manera segura, siguiendo las mejores prácticas:
- HttpOnly: JavaScript no puede acceder a las cookies
- Secure: Solo se envían por HTTPS
- SameSite: Protección contra CSRF
"""
import os
from fastapi import Response, Request
from typing import Optional
from datetime import datetime
from core.config import settings


# Configuración de cookies según el entorno
IS_PRODUCTION = os.getenv("ENV") != "development"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", None)  # .cisnaturatienda.com en producción

# Nombres de cookies
ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"
CSRF_TOKEN_COOKIE = "csrf_token"


def get_cookie_settings(is_refresh: bool = False) -> dict:
    """
    Obtener configuración de cookies según el entorno.
    
    Args:
        is_refresh: Si es True, usa tiempo de expiración más largo para refresh token
        
    Returns:
        dict con configuración de cookies
    """
    # Max age en segundos
    if is_refresh:
        max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    else:
        max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return {
        "httponly": True,  # JavaScript NO puede acceder
        "secure": IS_PRODUCTION,  # Solo HTTPS en producción
        "samesite": "lax",  # Permite redirects pero protege contra CSRF
        "max_age": max_age,
        "path": "/",
        "domain": COOKIE_DOMAIN if IS_PRODUCTION else None,
    }


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: Optional[str] = None
) -> None:
    """
    Establecer cookies de autenticación de manera segura.
    
    Args:
        response: Objeto Response de FastAPI
        access_token: JWT access token
        refresh_token: JWT refresh token
        csrf_token: Token CSRF opcional (para formularios)
    """
    # Cookie del access token (HttpOnly, no accesible por JS)
    access_settings = get_cookie_settings(is_refresh=False)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        **access_settings
    )
    
    # Cookie del refresh token (HttpOnly, duración más larga)
    refresh_settings = get_cookie_settings(is_refresh=True)
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        **refresh_settings
    )
    
    # CSRF token (NO HttpOnly - JavaScript necesita leerlo para enviarlo en headers)
    if csrf_token:
        response.set_cookie(
            key=CSRF_TOKEN_COOKIE,
            value=csrf_token,
            httponly=False,  # JS puede leer para enviarlo en header
            secure=IS_PRODUCTION,
            samesite="lax",
            max_age=access_settings["max_age"],
            path="/",
            domain=COOKIE_DOMAIN if IS_PRODUCTION else None,
        )


def clear_auth_cookies(response: Response) -> None:
    """
    Eliminar todas las cookies de autenticación.
    
    Args:
        response: Objeto Response de FastAPI
    """
    cookie_params = {
        "path": "/",
        "domain": COOKIE_DOMAIN if IS_PRODUCTION else None,
    }
    
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, **cookie_params)
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, **cookie_params)
    response.delete_cookie(key=CSRF_TOKEN_COOKIE, **cookie_params)


def get_token_from_cookie(request: Request, cookie_name: str = ACCESS_TOKEN_COOKIE) -> Optional[str]:
    """
    Obtener token de las cookies de la petición.
    
    Args:
        request: Objeto Request de FastAPI
        cookie_name: Nombre de la cookie a leer
        
    Returns:
        Token si existe, None si no
    """
    return request.cookies.get(cookie_name)


def get_access_token_from_request(request: Request) -> Optional[str]:
    """
    Obtener access token de la petición.
    Primero busca en cookies, luego en header Authorization.
    
    Args:
        request: Objeto Request de FastAPI
        
    Returns:
        Access token si se encuentra, None si no
    """
    # Primero intentar obtener de cookies HttpOnly
    token = get_token_from_cookie(request, ACCESS_TOKEN_COOKIE)
    
    if token:
        return token
    
    # Fallback: obtener del header Authorization (para compatibilidad)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    return None


def get_refresh_token_from_request(request: Request) -> Optional[str]:
    """
    Obtener refresh token de la petición (solo de cookies).
    
    Args:
        request: Objeto Request de FastAPI
        
    Returns:
        Refresh token si se encuentra, None si no
    """
    return get_token_from_cookie(request, REFRESH_TOKEN_COOKIE)
