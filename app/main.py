from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from contextlib import asynccontextmanager
from core.config import settings
from core.database import get_db
from models.admin_settings import AdminSettings

# Rutas de endpoints importadas
from routes.auth import router as auth_router
from routes.products import router as products_router
from routes.uploads import router as uploads_router
from routes.carts import router as carts_router
from routes.addresses import router as addresses_router
from routes.orders import router as orders_router
from routes.admin_orders import router as admin_orders_router
from routes.user import router as user_router
from routes.admin_settings import router as admin_settings_router
from routes.public_settings import router as public_settings_router
from routes.payments import router as payments_router

# Tareas automáticas
from core.tasks import start_scheduler, stop_scheduler

# Inicializar Firebase Admin SDK
from core.firebase_service import firebase_service
firebase_service.initialize()

# Inicializar Payment Service
from core.payment_service import payment_service

def initialize_payment_service():
    """
    Inicializa el servicio de pagos según el proveedor configurado.
    """
    provider = settings.PAYMENT_PROVIDER.lower()
    
    if provider == "stripe":
        payment_service.initialize(
            provider_name="stripe",
            api_key=settings.STRIPE_API_KEY,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET
        )
    else:
        raise ValueError(f"Unsupported payment provider: {provider}")

# Inicializar al arrancar la app
initialize_payment_service()

docs_url = "/docs" if os.getenv("ENV") == "development" else None
redoc_url = "/redoc" if os.getenv("ENV") == "development" else None
openapi_url = "/openapi.json" if os.getenv("ENV") == "development" else None

# ==================== LIFESPAN EVENTS ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el startup y shutdown de la aplicación.
    """
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    redirect_slashes=False,  # Evita redirects 307
    lifespan=lifespan  # Agregar lifespan
)

# CORS config - IMPORTANTE: allow_credentials=True necesario para cookies HttpOnly
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "https://cisnaturatienda.com")
if cors_origins.strip() == "*":
    allow_origins = ["https://cisnaturatienda.com"]
else:
    allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,  # Requerido para cookies cross-origin
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token"],  # Incluir header CSRF
)

# ==================== CSRF PROTECTION MIDDLEWARE ====================
# Descomenta la siguiente línea para habilitar protección CSRF
# Solo necesario si el frontend usa exclusivamente cookies (no Bearer token en header)
# from core.csrf_protection import CSRFMiddleware
# app.add_middleware(CSRFMiddleware)

# ==================== MAINTENANCE MODE MIDDLEWARE ====================

@app.middleware("http")
async def maintenance_mode_middleware(request: Request, call_next):
    """
    Middleware que bloquea peticiones de usuarios normales cuando
    el modo mantenimiento está activo.
    Los admins siempre pueden acceder.
    """
    # Rutas públicas que siempre deben estar disponibles
    public_paths = ["/", "/health", "/docs", "/openapi.json", "/static"]
    
    # Si es ruta pública, permitir
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # Obtener configuración de maintenance
    db = next(get_db())
    try:
        settings_obj = db.query(AdminSettings).first()
        
        if settings_obj and settings_obj.maintenance_mode:
            # Verificar si el usuario es admin
            auth_header = request.headers.get("Authorization")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                # Usuario no autenticado durante mantenimiento
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "success": False,
                        "status_code": 503,
                        "message": settings_obj.maintenance_message,
                        "error": "MAINTENANCE_MODE"
                    }
                )
            
            # Si tiene token, verificar si es admin
            from core.security import decode_token
            from models.user import User
            import uuid
            
            token = auth_header.replace("Bearer ", "")
            payload = decode_token(token)
            
            if payload:
                user_id = uuid.UUID(payload.get("sub"))
                user = db.query(User).filter(User.id == user_id).first()
                
                if user and user.is_admin:
                    # Admin puede acceder durante mantenimiento
                    return await call_next(request)
            
            # Usuario normal durante mantenimiento
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "success": False,
                    "status_code": 503,
                    "message": settings_obj.maintenance_message,
                    "error": "MAINTENANCE_MODE"
                }
            )
    finally:
        db.close()
    
    return await call_next(request)

# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Maneja errores de validación de Pydantic y los convierte al formato estándar.
    """
    errors = exc.errors()
    
    # Construir mensaje descriptivo
    error_messages = []
    validation_errors = []
    
    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"][1:])  # Omitir 'body'
        msg = error["msg"]
        error_type = error["type"]
        
        # Mensajes personalizados según el tipo de error
        if error_type == "string_too_short":
            min_length = error.get("ctx", {}).get("min_length", "")
            error_messages.append(f"El campo '{field}' debe tener al menos {min_length} caracteres")
        elif error_type == "string_too_long":
            max_length = error.get("ctx", {}).get("max_length", "")
            error_messages.append(f"El campo '{field}' debe tener máximo {max_length} caracteres")
        elif error_type == "missing":
            error_messages.append(f"El campo '{field}' es requerido")
        elif error_type == "value_error":
            error_messages.append(f"El campo '{field}' tiene un valor inválido")
        elif error_type == "type_error":
            expected_type = error.get("ctx", {}).get("expected", "válido")
            error_messages.append(f"El campo '{field}' debe ser de tipo {expected_type}")
        elif error_type.startswith("greater_than"):
            limit = error.get("ctx", {}).get("gt", "")
            error_messages.append(f"El campo '{field}' debe ser mayor que {limit}")
        elif error_type.startswith("less_than"):
            limit = error.get("ctx", {}).get("lt", "")
            error_messages.append(f"El campo '{field}' debe ser menor que {limit}")
        elif "email" in error_type.lower():
            error_messages.append(f"El campo '{field}' debe ser un email válido")
        else:
            error_messages.append(f"El campo '{field}': {msg}")
        
        # Agregar error detallado para debugging
        validation_errors.append({
            "field": field,
            "message": error_messages[-1],
            "type": error_type,
            "input": error.get("input")
        })
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "status_code": 400,
            "message": "Error de validación: " + "; ".join(error_messages),
            "error": "VALIDATION_ERROR",
            "details": validation_errors
        }
    )

# Registrar routers
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(uploads_router)
app.include_router(carts_router)
app.include_router(addresses_router)
app.include_router(orders_router)
app.include_router(admin_orders_router)
app.include_router(admin_settings_router)
app.include_router(public_settings_router)
app.include_router(user_router)
app.include_router(payments_router)

# Configurar directorio de uploads para servir archivos estáticos
# IMPORTANTE: Debe ir después de los routers para no capturar las rutas de API
uploads_path = Path(settings.UPLOAD_DIR)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(uploads_path)), name="static")

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Cisnatura API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}