from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from core.config import settings

# Rutas de endpoints importadas
from routes.auth import router as auth_router
from routes.products import router as products_router
from routes.uploads import router as uploads_router
from routes.carts import router as carts_router
from routes.addresses import router as addresses_router
from routes.orders import router as orders_router
from routes.admin_orders import router as admin_orders_router
from routes.user import router as user_router

# Inicializar Firebase Admin SDK
from core.firebase_service import firebase_service
firebase_service.initialize()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redirect_slashes=False  # Evita redirects 307
)

# CORS config
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
if cors_origins.strip() == "*":
    allow_origins = ["*"]
else:
    allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(user_router)

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