from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from core.config import settings

# Rutas de endpoints importadas
from routes.products import router as products_router

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs"
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
# Registrar routers
app.include_router(products_router)

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