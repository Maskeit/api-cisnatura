"""
Servicio para manejo de almacenamiento de archivos.
Optimiza imágenes automáticamente a formato WebP.
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException
from PIL import Image
import io


class StorageService:
    """Servicio para gestionar el almacenamiento de archivos."""
    
    def __init__(self):
        # Obtener ruta base desde variable de entorno o usar default
        # En producción con bind mounts: /home/admin/cisnatura/uploads
        # En desarrollo con volumen: /app/uploads
        upload_dir = os.getenv("UPLOAD_DIR", "/app/uploads")
        self.base_dir = Path(upload_dir)
        self.products_dir = self.base_dir / "products"
        self.categories_dir = self.base_dir / "categories"
        
        # Crear directorios si no existen
        self.products_dir.mkdir(parents=True, exist_ok=True)
        self.categories_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración de optimización
        self.max_size = (1920, 1920)  # Tamaño máximo
        self.quality = 85  # Calidad WebP
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        self.max_file_size = 5 * 1024 * 1024  # 5MB
    
    def _validate_image(self, file: UploadFile) -> None:
        """Validar que el archivo es una imagen válida"""
        # Verificar extensión
        ext = Path(file.filename).suffix.lower()
        if ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": f"Formato no permitido. Use: {', '.join(self.allowed_extensions)}",
                    "error": "INVALID_FILE_FORMAT"
                }
            )
        
        # Verificar content type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": "El archivo debe ser una imagen",
                    "error": "INVALID_CONTENT_TYPE"
                }
            )
    
    async def _optimize_image(self, file: UploadFile) -> bytes:
        """Optimizar imagen y convertir a WebP"""
        # Leer archivo
        contents = await file.read()
        
        # Verificar tamaño
        if len(contents) > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": f"El archivo es muy grande. Máximo: {self.max_file_size / (1024*1024)}MB",
                    "error": "FILE_TOO_LARGE"
                }
            )
        
        # Abrir imagen con Pillow
        try:
            image = Image.open(io.BytesIO(contents))
            
            # Convertir a RGB si es necesario (para WebP)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Redimensionar si es necesario
            if image.size[0] > self.max_size[0] or image.size[1] > self.max_size[1]:
                image.thumbnail(self.max_size, Image.Resampling.LANCZOS)
            
            # Guardar como WebP en memoria
            output = io.BytesIO()
            image.save(
                output,
                format='WEBP',
                quality=self.quality,
                method=6  # Mejor compresión
            )
            
            return output.getvalue()
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": f"Error al procesar imagen: {str(e)}",
                    "error": "IMAGE_PROCESSING_ERROR"
                }
            )
    
    async def save_product_image(self, file: UploadFile) -> str:
        """
        Guardar imagen de producto optimizada.
        Retorna solo el nombre del archivo (sin ruta completa).
        """
        self._validate_image(file)
        
        # Optimizar imagen
        optimized_data = await self._optimize_image(file)
        
        # Generar nombre único
        filename = f"{uuid.uuid4()}.webp"
        filepath = self.products_dir / filename
        
        # Guardar archivo
        with open(filepath, 'wb') as f:
            f.write(optimized_data)
        
        # Retornar solo el nombre del archivo
        return filename
    
    async def save_category_image(self, file: UploadFile) -> str:
        """
        Guardar imagen de categoría optimizada.
        Retorna solo el nombre del archivo (sin ruta completa).
        """
        self._validate_image(file)
        
        # Optimizar imagen
        optimized_data = await self._optimize_image(file)
        
        # Generar nombre único
        filename = f"{uuid.uuid4()}.webp"
        filepath = self.categories_dir / filename
        
        # Guardar archivo
        with open(filepath, 'wb') as f:
            f.write(optimized_data)
        
        # Retornar solo el nombre del archivo
        return filename
    
    def delete_file(self, filename: str) -> bool:
        """
        Eliminar un archivo de imagen.
        Acepta tanto rutas completas como solo nombres de archivo.
        Ejemplos:
            - "/static/products/uuid.webp"
            - "products/uuid.webp"
            - "uuid.webp"
        """
        if not filename:
            return False
        
        # Normalizar la ruta: eliminar /static/ si está presente
        if filename.startswith("/static/"):
            filename = filename.replace("/static/", "", 1)
        
        # Extraer solo el nombre del archivo si viene con ruta
        filename = str(filename).split('/')[-1]
        
        # Buscar en productos
        product_path = self.products_dir / filename
        if product_path.exists():
            try:
                product_path.unlink()
                return True
            except Exception:
                return False
        
        # Buscar en categorías
        category_path = self.categories_dir / filename
        if category_path.exists():
            try:
                category_path.unlink()
                return True
            except Exception:
                return False
        
        # Si no encontró el archivo, retorna False pero no falla
        return False


# Instancia singleton
storage_service = StorageService()
