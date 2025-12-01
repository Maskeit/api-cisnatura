"""
Rutas administrativas para configuraciones del sistema.
Solo accesibles por usuarios administradores.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from core.dependencies import get_current_admin_user
from models.admin_settings import AdminSettings
from models.user import User
from schemas.admin_settings import (
    AdminSettingsResponse,
    UpdateMaintenanceMode,
    UpdateShippingPrice,
    UpdateGlobalDiscount,
    AddCategoryDiscount,
    AddProductDiscount,
    AddSeasonalOffer,
    UpdateUserRegistration,
    UpdateMaxItemsPerOrder
)

router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])


def get_or_create_settings(db: Session) -> AdminSettings:
    """
    Obtener o crear el único registro de configuraciones.
    Solo debe existir UN registro en la tabla.
    """
    settings = db.query(AdminSettings).first()
    if not settings:
        # Crear configuración inicial con valores por defecto
        settings = AdminSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=AdminSettingsResponse)
async def get_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener todas las configuraciones administrativas.
    Requiere permisos de administrador.
    """
    settings = get_or_create_settings(db)
    return settings


@router.put("/maintenance", response_model=AdminSettingsResponse)
async def update_maintenance_mode(
    data: UpdateMaintenanceMode,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Activar/desactivar modo mantenimiento.
    Cuando está activo, solo los admins pueden usar la API.
    """
    settings = get_or_create_settings(db)
    settings.maintenance_mode = data.maintenance_mode
    
    if data.maintenance_message:
        settings.maintenance_message = data.maintenance_message
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    return settings


@router.put("/shipping", response_model=AdminSettingsResponse)
async def update_shipping_price(
    data: UpdateShippingPrice,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Actualizar precio de envío y umbral para envío gratis.
    """
    settings = get_or_create_settings(db)
    settings.shipping_price = data.shipping_price
    settings.free_shipping_threshold = data.free_shipping_threshold
    settings.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.put("/discount/global", response_model=AdminSettingsResponse)
async def update_global_discount(
    data: UpdateGlobalDiscount,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Configurar descuento global en todos los productos.
    """
    settings = get_or_create_settings(db)
    settings.global_discount_enabled = data.enabled
    settings.global_discount_percentage = data.percentage
    settings.global_discount_name = data.name
    settings.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.post("/discount/category", response_model=AdminSettingsResponse)
async def add_category_discount(
    data: AddCategoryDiscount,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Agregar o actualizar descuento para una categoría específica.
    """
    settings = get_or_create_settings(db)
    
    # Actualizar o agregar descuento en el JSON
    if settings.category_discounts is None:
        settings.category_discounts = {}
    
    settings.category_discounts[data.category_id] = {
        "percentage": data.percentage,
        "name": data.name
    }
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    return settings


@router.delete("/discount/category/{category_id}", response_model=AdminSettingsResponse)
async def remove_category_discount(
    category_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Eliminar descuento de una categoría.
    """
    settings = get_or_create_settings(db)
    
    if settings.category_discounts and category_id in settings.category_discounts:
        del settings.category_discounts[category_id]
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
    
    return settings


@router.post("/discount/product", response_model=AdminSettingsResponse)
async def add_product_discount(
    data: AddProductDiscount,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Agregar o actualizar descuento para un producto específico.
    """
    settings = get_or_create_settings(db)
    
    if settings.product_discounts is None:
        settings.product_discounts = {}
    
    settings.product_discounts[data.product_id] = {
        "percentage": data.percentage,
        "name": data.name
    }
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    return settings


@router.delete("/discount/product/{product_id}", response_model=AdminSettingsResponse)
async def remove_product_discount(
    product_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Eliminar descuento de un producto.
    """
    settings = get_or_create_settings(db)
    
    if settings.product_discounts and product_id in settings.product_discounts:
        del settings.product_discounts[product_id]
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
    
    return settings


@router.post("/seasonal-offer", response_model=AdminSettingsResponse)
async def add_seasonal_offer(
    data: AddSeasonalOffer,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Crear una oferta temporal/estacional (ej: Black Friday, Navidad).
    """
    settings = get_or_create_settings(db)
    
    if settings.seasonal_offers is None:
        settings.seasonal_offers = []
    
    # Agregar nueva oferta
    offer = {
        "name": data.name,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "discount_percentage": data.discount_percentage,
        "category_ids": data.category_ids,
        "product_ids": data.product_ids
    }
    
    settings.seasonal_offers.append(offer)
    settings.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.delete("/seasonal-offer/{offer_name}", response_model=AdminSettingsResponse)
async def remove_seasonal_offer(
    offer_name: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Eliminar una oferta temporal por nombre.
    """
    settings = get_or_create_settings(db)
    
    if settings.seasonal_offers:
        settings.seasonal_offers = [
            offer for offer in settings.seasonal_offers
            if offer.get("name") != offer_name
        ]
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
    
    return settings


@router.put("/user-registration", response_model=AdminSettingsResponse)
async def update_user_registration(
    data: UpdateUserRegistration,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Activar/desactivar registro de nuevos usuarios.
    """
    settings = get_or_create_settings(db)
    settings.allow_user_registration = data.allow_user_registration
    settings.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.put("/max-items", response_model=AdminSettingsResponse)
async def update_max_items_per_order(
    data: UpdateMaxItemsPerOrder,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Actualizar límite de productos por orden.
    """
    settings = get_or_create_settings(db)
    settings.max_items_per_order = data.max_items_per_order
    settings.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.get("/test-discount/{product_id}")
async def test_product_discount(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Endpoint de prueba para verificar descuentos en un producto.
    Muestra el cálculo detallado.
    """
    from models.products import Product
    from core.discount_service import calculate_product_discount
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    settings = get_or_create_settings(db)
    final_price, discount_info = calculate_product_discount(product, settings)
    
    return {
        "success": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "category_id": product.category_id,
            "original_price": float(product.price)
        },
        "settings": {
            "global_discount_enabled": settings.global_discount_enabled,
            "global_discount_percentage": settings.global_discount_percentage,
            "category_discounts": settings.category_discounts,
            "product_discounts": settings.product_discounts,
            "seasonal_offers": settings.seasonal_offers
        },
        "calculated": {
            "final_price": final_price,
            "discount_info": discount_info
        }
    }
