"""
Endpoints de autenticación: registro, login, verificación de email.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token, create_refresh_token
from core.email_service import email_service
from core.config import settings
from core.dependencies import get_current_user
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
security = HTTPBearer()

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
    db: Session = Depends(get_db)
):
    """
    Iniciar sesión con email y contraseña.
    
    - Requiere email verificado
    - Retorna access_token y refresh_token
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
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Login exitoso",
        "data": {
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
    
    Requiere autenticación (Bearer token).
    """
    return current_user


# ==================== LOGOUT ====================

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
):
    """
    Cerrar sesión (revocar token actual).
    
    - El token se agrega a una blacklist en Redis
    - El token permanece inválido hasta su expiración natural
    - El usuario deberá hacer login nuevamente para obtener un nuevo token
    """
    from core.redis_service import TokenBlacklistService
    from core.security import decode_token
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload and "jti" in payload and "exp" in payload:
        # Calcular segundos hasta la expiración
        from datetime import datetime
        exp_timestamp = payload["exp"]
        now_timestamp = datetime.utcnow().timestamp()
        expires_in_seconds = int(exp_timestamp - now_timestamp)
        
        # Solo agregar a blacklist si el token aún no ha expirado
        if expires_in_seconds > 0:
            TokenBlacklistService.revoke_token(
                token_jti=payload["jti"],
                expires_in_seconds=expires_in_seconds
            )
    
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
    db: Session = Depends(get_db)
):
    """
    Iniciar sesión o registrarse con Google (Firebase).
    
    - Verifica el token de Firebase
    - Si el usuario existe, retorna tokens de acceso
    - Si el usuario no existe, lo crea automáticamente
    - No requiere verificación de email (Google ya lo verificó)
    
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
    
    # 7. Retornar respuesta
    return {
        "success": True,
        "status_code": 200,
        "message": "Login con Google exitoso" if not is_new_user else "Cuenta creada con Google exitosamente",
        "data": {
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