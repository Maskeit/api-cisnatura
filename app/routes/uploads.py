"""
Endpoints para subir archivos (imágenes).
"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from pathlib import Path
import uuid
import os
from typing import List
from PIL import Image
import io
from core.config import settings
from core.dependencies import get_current_admin_user
from models.user import User

router = APIRouter(
    prefix="/uploads",
    tags=["uploads"]
)

# Configuración de uploads
UPLOAD_DIR = Path(settings.UPLOAD_DIR)  # /app/uploads
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
IMAGE_QUALITY = 85  # Calidad de compresión


def validate_image(file: UploadFile) -> None:
    """
    Validar que el archivo sea una imagen válida.
    """
    # Validar extensión
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"Tipo de archivo no permitido. Solo se permiten: {', '.join(ALLOWED_EXTENSIONS)}",
                "error": "INVALID_FILE_TYPE"
            }
        )
    
    # Validar tipo MIME
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El archivo debe ser una imagen",
                "error": "INVALID_CONTENT_TYPE"
            }
        )


async def save_image(file: UploadFile, subfolder: str = "products") -> str:
    """
    Guardar imagen en el servidor.
    
    Args:
        file: Archivo subido
        subfolder: Subcarpeta donde guardar (products, categories, etc.)
    
    Returns:
        Ruta relativa de la imagen guardada
    """
    # Crear directorio si no existe
    upload_path = UPLOAD_DIR / subfolder
    upload_path.mkdir(parents=True, exist_ok=True)
    
    # Leer contenido del archivo
    contents = await file.read()
    
    # Validar tamaño
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"El archivo es demasiado grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB",
                "error": "FILE_TOO_LARGE"
            }
        )
    
    # Generar nombre único
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_path / unique_filename
    
    try:
        # Abrir y procesar imagen con Pillow
        image = Image.open(io.BytesIO(contents))
        
        # Convertir RGBA a RGB si es necesario
        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background
        
        # Redimensionar si es muy grande (mantener aspecto)
        max_dimension = 1920
        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        # Guardar con compresión
        image.save(
            file_path,
            format="JPEG" if file_ext in [".jpg", ".jpeg"] else image.format,
            quality=IMAGE_QUALITY,
            optimize=True
        )
        
        # Retornar ruta relativa
        return f"/static/{subfolder}/{unique_filename}"
    
    except Exception as e:
        # Eliminar archivo si hubo error
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"Error al procesar la imagen: {str(e)}",
                "error": "IMAGE_PROCESSING_ERROR"
            }
        )


@router.post("/products", status_code=201)
async def upload_product_image(
    file: UploadFile = File(..., description="Archivo de imagen"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Subir imagen de producto (solo administradores).
    
    - Formatos permitidos: JPG, JPEG, PNG, WEBP, GIF
    - Tamaño máximo: 5MB
    - La imagen se redimensiona automáticamente si es muy grande
    - Se comprime para optimizar el almacenamiento
    
    Retorna la URL relativa de la imagen guardada.
    """
    # Validar imagen
    validate_image(file)
    
    # Guardar imagen
    file_url = await save_image(file, subfolder="products")
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Imagen subida exitosamente",
        "data": {
            "file_url": file_url,
            "filename": file.filename,
            "content_type": file.content_type
        }
    }


@router.post("/categories", status_code=201)
async def upload_category_image(
    file: UploadFile = File(..., description="Archivo de imagen"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Subir imagen de categoría (solo administradores).
    
    - Formatos permitidos: JPG, JPEG, PNG, WEBP, GIF
    - Tamaño máximo: 5MB
    """
    validate_image(file)
    file_url = await save_image(file, subfolder="categories")
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Imagen subida exitosamente",
        "data": {
            "file_url": file_url,
            "filename": file.filename,
            "content_type": file.content_type
        }
    }


@router.delete("/")
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar un archivo del servidor (solo administradores).
    
    - file_path: Ruta relativa del archivo (ej: /static/products/abc123.jpg)
    """
    # Validar que la ruta empiece con /static/
    if not file_path.startswith("/static/"):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "Ruta de archivo inválida",
                "error": "INVALID_FILE_PATH"
            }
        )
    
    # Convertir ruta relativa a absoluta
    relative_path = file_path.replace("/static/", "")
    full_path = UPLOAD_DIR / relative_path
    
    # Verificar que el archivo existe
    if not full_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Archivo no encontrado",
                "error": "FILE_NOT_FOUND"
            }
        )
    
    # Eliminar archivo
    try:
        full_path.unlink()
        return {
            "success": True,
            "status_code": 200,
            "message": "Archivo eliminado exitosamente",
            "data": {
                "file_path": file_path
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "status_code": 500,
                "message": f"Error al eliminar archivo: {str(e)}",
                "error": "DELETE_ERROR"
            }
        )
