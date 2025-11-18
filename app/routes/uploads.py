"""
Endpoints para manejo de uploads de imágenes.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from core.storage import storage_service
from core.database import get_db
from models.products import Product, Category

router = APIRouter(
    prefix="/uploads",
    tags=["uploads"]
)


@router.post("/products/{product_id}/image")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # TODO: Agregar autenticación
    # current_user: User = Depends(get_current_admin_user)
):
    """
    Subir imagen para un producto (solo administradores).
    
    - Convierte automáticamente a WebP
    - Optimiza el tamaño y calidad
    - Elimina la imagen anterior si existe
    
    Requiere autenticación y rol de administrador.
    """
    # TODO: Verificar que current_user.is_admin == True
    
    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado",
                "error": "PRODUCT_NOT_FOUND"
            }
        )
    
    # Eliminar imagen anterior si existe
    if product.image_url:
        storage_service.delete_file(product.image_url)
    
    # Guardar nueva imagen optimizada (solo retorna el nombre del archivo)
    filename = await storage_service.save_product_image(file)
    
    # Actualizar producto con solo el nombre del archivo
    product.image_url = filename
    db.commit()
    db.refresh(product)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Imagen subida exitosamente",
        "data": {
            "product_id": product.id,
            "image_url": filename,  # Solo el nombre del archivo
            "full_url": f"/static/products/{filename}"  # URL completa para referencia
        }
    }


@router.post("/categories/{category_id}/image")
async def upload_category_image(
    category_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # TODO: Agregar autenticación
    # current_user: User = Depends(get_current_admin_user)
):
    """
    Subir imagen para una categoría (solo administradores).
    
    - Convierte automáticamente a WebP
    - Optimiza el tamaño y calidad
    - Elimina la imagen anterior si existe
    
    Requiere autenticación y rol de administrador.
    """
    # TODO: Verificar que current_user.is_admin == True
    
    # Verificar que la categoría existe
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Categoría no encontrada",
                "error": "CATEGORY_NOT_FOUND"
            }
        )
    
    # Eliminar imagen anterior si existe
    if category.image_url:
        storage_service.delete_file(category.image_url)
    
    # Guardar nueva imagen optimizada (solo retorna el nombre del archivo)
    filename = await storage_service.save_category_image(file)
    
    # Actualizar categoría con solo el nombre del archivo
    category.image_url = filename
    db.commit()
    db.refresh(category)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Imagen subida exitosamente",
        "data": {
            "category_id": category.id,
            "image_url": filename,  # Solo el nombre del archivo
            "full_url": f"/static/categories/{filename}"  # URL completa para referencia
        }
    }


@router.delete("/products/{product_id}/image")
async def delete_product_image(
    product_id: int,
    db: Session = Depends(get_db),
    # TODO: Agregar autenticación
    # current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar imagen de un producto (solo administradores).
    
    Requiere autenticación y rol de administrador.
    """
    # TODO: Verificar que current_user.is_admin == True
    
    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado",
                "error": "PRODUCT_NOT_FOUND"
            }
        )
    
    if not product.image_url:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "El producto no tiene imagen",
                "error": "NO_IMAGE_FOUND"
            }
        )
    
    # Eliminar archivo físico
    storage_service.delete_file(product.image_url)
    
    # Actualizar producto
    product.image_url = None
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Imagen eliminada exitosamente",
        "data": {
            "product_id": product.id
        }
    }
