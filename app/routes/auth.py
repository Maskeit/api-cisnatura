"""
Endpoints de autenticación: registro, login, verificación de email.

Seguridad de sesiones:
- Cookies HttpOnly para access_token y refresh_token
- Protección CSRF para requests con cookies
- Soporte dual: cookies HttpOnly + Bearer token (para APIs móviles)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from core.email_service import email_service
from core.config import settings
from core.dependencies import get_current_user
from core.cookie_auth import (
    set_auth_cookies,
    clear_auth_cookies,
    get_refresh_token_from_request,
    get_access_token_from_request
)
from core.csrf_protection import generate_csrf_token
from models.user import User
from models.email_verification import EmailVerificationToken
from schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
    UserResponse,
    GoogleLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)

# Security scheme para logout
security = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


# ==================== REGISTRO ====================

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Registrar un nuevo usuario.
    
    - Crea el usuario con email_verified=False
    - Genera token de verificación
    - Envía email de confirmación
    """
    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El email ya está registrado",
                "error": "EMAIL_ALREADY_EXISTS"
            }
        )
    
    # Crear nuevo usuario
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_admin=False,
        email_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generar token de verificación
    verification_token = EmailVerificationToken.generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    token_record = EmailVerificationToken(
        user_id=new_user.id,
        token=verification_token,
        expires_at=expires_at
    )
    
    db.add(token_record)
    db.commit()
    
    # Enviar email de verificación (asíncrono, no bloquea la respuesta)
    try:
        await email_service.send_verification_email(
            to_email=new_user.email,
            full_name=new_user.full_name,
            verification_token=verification_token
        )
    except Exception as e:
        print(f"Error al enviar email de verificación: {e}")
        # No falla el registro si el email no se envía
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Usuario registrado exitosamente. Revisa tu correo para verificar tu cuenta.",
        "data": {
            "user_id": str(new_user.id),
            "email": new_user.email,
            "email_verified": new_user.email_verified
        }
    }


# ==================== VERIFICACIÓN DE EMAIL ====================

@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verificar email con el token recibido por correo.
    """
    # Buscar token
    token_record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == request.token,
        EmailVerificationToken.is_used == False
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "status_code": 400,
                "message": "Token inválido o ya utilizado",
                "error": "INVALID_TOKEN"
            }
        )
    
    # Verificar expiración
    if token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El token ha expirado",
                "error": "TOKEN_EXPIRED"
            }
        )
    
    # Actualizar usuario
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Usuario no encontrado",
                "error": "USER_NOT_FOUND"
            }
        )
    
    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    
    # Marcar token como usado
    token_record.is_used = True
    token_record.used_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Email verificado exitosamente. Ya puedes iniciar sesión.",
        "data": {
            "email_verified": True
        }
    }

# ==================== VERIFICACION DE EMAIL PARA RESET PASSWORD
@router.post("/validate-email-reset")
async def validate_reset_token(
    request: VerifyEmailRequest,  # Reutilizas este schema
    db: Session = Depends(get_db)
):
    """
    Validar que el token de reset sea válido antes de mostrar el formulario.
    """
    token_record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == request.token,
        EmailVerificationToken.is_used == False
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Token inválido o ya utilizado",
                "error": "INVALID_TOKEN"
            }
        )
    
    if token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "El token ha expirado",
                "error": "TOKEN_EXPIRED"
            }
        )
    
    return {
        "success": True,
        "message": "Token válido",
        "data": {
            "email": token_record.user.email  # Para mostrarlo en el formulario
        }
    }


# ==================== REENVIAR VERIFICACIÓN ====================

@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Reenviar email de verificación.
    """
    # Buscar usuario
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Por seguridad, no revelamos si el email existe
        return {
            "success": True,
            "status_code": 200,
            "message": "Si el email existe, recibirás un correo de verificación."
        }
    
    # Verificar si ya está verificado
    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El email ya está verificado",
                "error": "EMAIL_ALREADY_VERIFIED"
            }
        )
    
    # Invalidar tokens anteriores
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.is_used == False
    ).update({"is_used": True})
    
    # Generar nuevo token
    verification_token = EmailVerificationToken.generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    token_record = EmailVerificationToken(
        user_id=user.id,
        token=verification_token,
        expires_at=expires_at
    )
    
    db.add(token_record)
    db.commit()
    
    # Enviar email
    try:
        await email_service.send_verification_email(
            to_email=user.email,
            full_name=user.full_name,
            verification_token=verification_token
        )
    except Exception as e:
        print(f"Error al enviar email: {e}")
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Email de verificación enviado."
    }


# ==================== LOGIN ====================

@router.post("/login")
async def login(
    credentials: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Iniciar sesión con email y contraseña.
    
    Seguridad:
    - Requiere email verificado
    - Establece cookies HttpOnly para access_token y refresh_token
    - Genera token CSRF para protección de formularios
    - También retorna tokens en body para compatibilidad con APIs móviles
    
    Cookies establecidas (HttpOnly, Secure, SameSite=Lax):
    - access_token: JWT de acceso
    - refresh_token: JWT de refresh (larga duración)
    - csrf_token: Token para protección CSRF (NO HttpOnly, JS puede leerlo)
    """
    # Buscar usuario
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Credenciales inválidas",
                "error": "INVALID_CREDENTIALS"
            }
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
    
    # Verificar que el email esté verificado
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "status_code": 403,
                "message": "Debes verificar tu email antes de iniciar sesión",
                "error": "EMAIL_NOT_VERIFIED"
            }
        )
    
    # Crear tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin
        }
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id)
        }
    )
    
    # Generar token CSRF
    csrf_token = generate_csrf_token()
    
    # Establecer cookies HttpOnly seguras
    set_auth_cookies(response, access_token, refresh_token, csrf_token)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Login exitoso",
        "data": {
            # Tokens en body para compatibilidad con apps móviles/APIs externas
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "email_verified": user.email_verified
            }
        }
    }


# ==================== PERFIL DE USUARIO ====================

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener información del usuario autenticado.
    
    Requiere autenticación (Bearer token o Cookie HttpOnly).
    """
    return current_user


# ==================== REFRESH TOKEN ====================

@router.post("/refresh")
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Refrescar el access token usando el refresh token.
    
    Soporta:
    1. Refresh token en cookie HttpOnly (automático)
    2. Refresh token en body JSON (para apps móviles)
    
    Seguridad:
    - Valida que el refresh token sea válido y no esté expirado
    - Verifica que el usuario siga activo
    - Genera nuevos tokens y actualiza cookies
    """
    from schemas.auth import RefreshTokenRequest
    
    # Intentar obtener refresh token de cookies
    refresh_token = get_refresh_token_from_request(request)
    
    # Fallback: intentar obtener del body
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except Exception:
            pass
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Refresh token requerido",
                "error": "REFRESH_TOKEN_REQUIRED"
            }
        )
    
    # Validar el refresh token
    from core.security import verify_token_type
    
    payload = decode_token(refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Refresh token inválido o expirado",
                "error": "INVALID_REFRESH_TOKEN"
            }
        )
    
    # Verificar que es un token de tipo refresh
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Token inválido (no es refresh token)",
                "error": "INVALID_TOKEN_TYPE"
            }
        )
    
    # Obtener usuario
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Token inválido",
                "error": "INVALID_TOKEN"
            }
        )
    
    import uuid
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
            }
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "Usuario no encontrado o inactivo",
                "error": "USER_NOT_FOUND"
            }
        )
    
    # Crear nuevos tokens
    new_access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin
        }
    )
    
    new_refresh_token = create_refresh_token(
        data={
            "sub": str(user.id)
        }
    )
    
    # Generar nuevo CSRF token y establecer cookies
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, new_access_token, new_refresh_token, csrf_token)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Tokens actualizados exitosamente",
        "data": {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    }


# ==================== LOGOUT ====================

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
):
    """
    Cerrar sesión (revocar token actual).
    
    Seguridad:
    - Elimina cookies HttpOnly de autenticación
    - Agrega el token a blacklist en Redis
    - El token permanece inválido hasta su expiración natural
    """
    from core.redis_service import TokenBlacklistService
    
    # Obtener token de cookies o header
    token = get_access_token_from_request(request)
    if not token and credentials:
        token = credentials.credentials
    
    if token:
        payload = decode_token(token)
        
        if payload and "jti" in payload and "exp" in payload:
            # Calcular segundos hasta la expiración
            exp_timestamp = payload["exp"]
            now_timestamp = datetime.now(timezone.utc).timestamp()
            expires_in_seconds = int(exp_timestamp - now_timestamp)
            
            # Solo agregar a blacklist si el token aún no ha expirado
            if expires_in_seconds > 0:
                TokenBlacklistService.revoke_token(
                    token_jti=payload["jti"],
                    expires_in_seconds=expires_in_seconds
                )
    
    # Limpiar cookies de autenticación
    clear_auth_cookies(response)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Sesión cerrada exitosamente"
    }

# ==================== SOLICITUD PARA RECUPERAR CUENTA ===================
@router.post("/recover-password")
async def recover_pass(
    user_data:ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Docstring para recover_pass
    
    :param user_data: Descripción
    :type user_data: ForgotPasswordRequest
    :param db: Descripción
    :type db: Session
    """
    # Verificar si el email ya existe y si no entonces notificar
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "status_code": 400,
                "message": "Este email no existe",
                "error": "EMAIL_NOT_EXISTS"
            }
        )
    
    # Generar token de verificación
    verification_token = EmailVerificationToken.generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    token_record = EmailVerificationToken(
        user_id=existing_user.id,
        token=verification_token,
        expires_at=expires_at
    )
    
    db.add(token_record)
    db.commit()
    # Enviar email de recuperación de contraseña
    try:
        await email_service.send_password_reset_email(
            to_email=existing_user.email,
            full_name=existing_user.full_name,
            reset_token=verification_token
        )
    except Exception as e:
        print(f"Error al enviar email de recuperación: {e}")
        # No falla la solicitud si el email no se envía
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Usuario validado exitosamente. Revisa tu correo para verificar tu cuenta.",
        "data": {
            "user_id": str(existing_user.id),
            "email": existing_user.email,
            "email_verified": existing_user.email_verified
        }
    }
    # retornar verify-email para poder reestablecer contrasena

# ==================== CAMBIO DE CONTRASENA ======================
@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,  # Ya tienes este schema
    db: Session = Depends(get_db)
):
    """
    Resetear contraseña usando el token del email.
    """
    # 1. Buscar token
    token_record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == request.token,
        EmailVerificationToken.is_used == False
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Token inválido o ya utilizado",
                "error": "INVALID_TOKEN"
            }
        )
    
    # 2. Verificar expiración
    if token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "El token ha expirado. Solicita uno nuevo.",
                "error": "TOKEN_EXPIRED"
            }
        )
    
    # 3. Obtener usuario
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "Usuario no encontrado",
                "error": "USER_NOT_FOUND"
            }
        )
    
    # 4. Actualizar contraseña
    user.hashed_password = hash_password(request.new_password)
    
    # 5. Marcar token como usado
    token_record.is_used = True
    token_record.used_at = datetime.now(timezone.utc)
    
    # 6. Invalidar todos los tokens de acceso anteriores (opcional pero recomendado)
    # Esto fuerza al usuario a hacer login nuevamente
    from core.redis_service import TokenBlacklistService
    # TokenBlacklistService.revoke_all_user_tokens(str(user.id))
    
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Contraseña actualizada exitosamente. Ya puedes iniciar sesión.",
        "data": {
            "email": user.email
        }
    }    
    
# ==================== GOOGLE AUTH ====================

@router.post("/google-login")
async def google_login(
    request: GoogleLoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Iniciar sesión o registrarse con Google (Firebase).
    
    Seguridad:
    - Token de Firebase se valida en BACKEND con firebase-admin SDK
    - NUNCA confiar solo en validación del frontend
    - Después de validar Firebase, se emite token JWT propio de la app
    - Establece cookies HttpOnly igual que el login normal
    
    Flujo:
    1. Frontend obtiene token de Firebase (Google SSO)
    2. Frontend envía token a este endpoint
    3. Backend valida token con Firebase Admin SDK
    4. Backend crea/actualiza usuario
    5. Backend emite sus propios tokens JWT + cookies HttpOnly
    
    Returns:
        - access_token: Token JWT de la aplicación
        - refresh_token: Token de refresh
        - user: Información del usuario
        - is_new_user: True si el usuario fue creado en esta petición
    """
    from core.firebase_service import firebase_service
    
    # 1. Verificar token de Firebase
    firebase_user = firebase_service.verify_token(request.firebase_token)
    
    if not firebase_user or not firebase_user.get("email"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "status_code": 401,
                "message": "No se pudo obtener información del usuario de Google",
                "error": "GOOGLE_USER_INFO_MISSING"
            }
        )
    
    email = firebase_user["email"]
    firebase_uid = firebase_user["uid"]
    full_name = firebase_user.get("name", email.split("@")[0])
    profile_image = firebase_user.get("picture")
    email_verified = firebase_user.get("email_verified", True)
    
    # 2. Buscar usuario existente por email o firebase_uid
    user = db.query(User).filter(
        (User.email == email) | (User.firebase_uid == firebase_uid)
    ).first()
    
    is_new_user = False
    
    # 3. Si el usuario no existe, crearlo
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            firebase_uid=firebase_uid,
            auth_provider="google",
            profile_image=profile_image,
            email_verified=email_verified,
            email_verified_at=datetime.now(timezone.utc) if email_verified else None,
            is_active=True,
            is_admin=False,
            hashed_password=None  # No hay contraseña para usuarios de Google
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new_user = True
        print(f"✅ Nuevo usuario creado con Google: {email}")
    
    # 4. Si el usuario existe pero no tiene firebase_uid, vincularlo
    elif not user.firebase_uid:
        user.firebase_uid = firebase_uid
        user.auth_provider = "google"
        if not user.email_verified:
            user.email_verified = email_verified
            user.email_verified_at = datetime.now(timezone.utc) if email_verified else None
        if profile_image and not user.profile_image:
            user.profile_image = profile_image
        db.commit()
        db.refresh(user)
        print(f"✅ Usuario vinculado con Google: {email}")
    
    # 5. Verificar que el usuario esté activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "status_code": 403,
                "message": "Usuario inactivo. Contacta con soporte.",
                "error": "USER_INACTIVE"
            }
        )
    
    # 6. Crear tokens JWT propios de la aplicación
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin
        }
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id)
        }
    )
    
    # 7. Generar token CSRF y establecer cookies HttpOnly
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, access_token, refresh_token, csrf_token)
    
    # 8. Retornar respuesta
    return {
        "success": True,
        "status_code": 200,
        "message": "Login con Google exitoso" if not is_new_user else "Cuenta creada con Google exitosamente",
        "data": {
            # Tokens en body para compatibilidad con apps móviles
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "email_verified": user.email_verified,
                "auth_provider": user.auth_provider,
                "profile_image": user.profile_image
            },
            "is_new_user": is_new_user
        }
    }