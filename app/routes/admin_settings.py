"""
Rutas administrativas para configuraciones del sistema.
Solo accesibles por usuarios administradores.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, attributes
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
    UpdateCategoriesNoShipping,
    UpdateGlobalDiscount,
    AddCategoryDiscount,
    AddProductDiscount,
    AddSeasonalOffer,
    UpdateUserRegistration,
    UpdateMaxItemsPerOrder,
    MaintenanceResponse,
    ShippingResponse,
    GlobalDiscountResponse,
    CategoryDiscountResponse,
    ProductDiscountResponse,
    SeasonalOfferResponse
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


@router.get("/maintenance")
async def get_maintenance_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener configuración de modo mantenimiento.
    """
    settings = get_or_create_settings(db)
    return {
        "success": True,
        "status_code": 200,
        "message": "Configuración de mantenimiento obtenida exitosamente",
        "data": {
            "maintenance_mode": settings.maintenance_mode,
            "maintenance_message": settings.maintenance_message
        }
    }


@router.get("/shipping")
async def get_shipping_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener configuración de envío.
    """
    settings = get_or_create_settings(db)
    return {
        "success": True,
        "status_code": 200,
        "message": "Configuración de envío obtenida exitosamente",
        "data": {
            "shipping_price": settings.shipping_price,
            "free_shipping_threshold": settings.free_shipping_threshold
        }
    }


@router.get("/discounts")
async def get_all_discounts(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener todos los descuentos (global, categorías y productos).
    Ideal para el panel de gestión de descuentos.
    """
    settings = get_or_create_settings(db)
    return {
        "success": True,
        "status_code": 200,
        "message": "Descuentos obtenidos exitosamente",
        "data": {
            "global_discount": {
                "enabled": settings.global_discount_enabled,
                "percentage": settings.global_discount_percentage,
                "name": settings.global_discount_name
            },
            "category_discounts": settings.category_discounts or {},
            "product_discounts": settings.product_discounts or {}
        }
    }


@router.get("/discount/global")
async def get_global_discount(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener solo el descuento global.
    """
    settings = get_or_create_settings(db)
    return {
        "success": True,
        "status_code": 200,
        "message": "Descuento global obtenido exitosamente",
        "data": {
            "enabled": settings.global_discount_enabled,
            "percentage": settings.global_discount_percentage,
            "name": settings.global_discount_name
        }
    }


@router.get("/discount/categories")
async def get_category_discounts(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener todos los descuentos por categoría.
    Devuelve un diccionario con category_id como clave.
    """
    settings = get_or_create_settings(db)
    return {
        "success": True,
        "status_code": 200,
        "message": "Descuentos por categoría obtenidos exitosamente",
        "data": {
            "category_discounts": settings.category_discounts or {}
        }
    }


@router.get("/discount/products")
async def get_product_discounts(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener todos los descuentos por producto.
    Devuelve un diccionario con product_id como clave.
    """
    settings = get_or_create_settings(db)
    return {
        "success": True,
        "status_code": 200,
        "message": "Descuentos por producto obtenidos exitosamente",
        "data": {
            "product_discounts": settings.product_discounts or {}
        }
    }


@router.get("/seasonal-offers")
async def get_seasonal_offers(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener todas las ofertas temporales/estacionales.
    """
    settings = get_or_create_settings(db)
    return {
        "success": True,
        "status_code": 200,
        "message": "Ofertas temporales obtenidas exitosamente",
        "data": {
            "seasonal_offers": settings.seasonal_offers or []
        }
    }


@router.get("/registration")
async def get_registration_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener configuración de registro de usuarios.
    """
    settings = get_or_create_settings(db)
    return {
        "success": True,
        "status_code": 200,
        "message": "Configuración de registro obtenida exitosamente",
        "data": {
            "allow_user_registration": settings.allow_user_registration,
            "max_items_per_order": settings.max_items_per_order
        }
    }


@router.put("/maintenance")
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
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Modo mantenimiento actualizado exitosamente",
        "data": {
            "maintenance_mode": settings.maintenance_mode,
            "maintenance_message": settings.maintenance_message
        }
    }


@router.put("/shipping")
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
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Precio de envío actualizado exitosamente",
        "data": {
            "shipping_price": settings.shipping_price,
            "free_shipping_threshold": settings.free_shipping_threshold
        }
    }


@router.put("/shipping/no-shipping-categories")
async def update_categories_no_shipping(
    data: UpdateCategoriesNoShipping,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Actualizar categorías que no pagan envío (productos digitales)"""
    settings = get_or_create_settings(db)
    settings.categories_no_shipping = data.category_ids
    settings.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(settings)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categorías sin envío actualizadas exitosamente",
        "data": {
            "categories_no_shipping": settings.categories_no_shipping
        }
    }


@router.put("/discount/global")
async def update_global_discount(
    data: UpdateGlobalDiscount,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Configurar descuento global en todos los productos.
    Si se activa, elimina todos los descuentos específicos.
    """
    settings = get_or_create_settings(db)
    settings.global_discount_enabled = data.enabled
    settings.global_discount_percentage = data.percentage
    settings.global_discount_name = data.name
    
    # Si se activa descuento global, limpiar otros descuentos
    if data.enabled:
        settings.category_discounts = {}
        settings.product_discounts = {}
        settings.seasonal_offers = []
        # Marcar columnas JSON como modificadas
        attributes.flag_modified(settings, "category_discounts")
        attributes.flag_modified(settings, "product_discounts")
        attributes.flag_modified(settings, "seasonal_offers")
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Descuento global actualizado exitosamente",
        "data": {
            "enabled": settings.global_discount_enabled,
            "percentage": settings.global_discount_percentage,
            "name": settings.global_discount_name
        }
    }


@router.post("/discount/category")
async def add_category_discount(
    data: AddCategoryDiscount,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Agregar o actualizar descuento para una categoría específica.
    No se puede agregar si hay un descuento global activo.
    """
    settings = get_or_create_settings(db)
    
    # Validar que no haya descuento global activo
    if settings.global_discount_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "status_code": 400,
                "message": "No se pueden agregar descuentos por categoría mientras hay un descuento global activo. Desactiva el descuento global primero.",
                "error": "GLOBAL_DISCOUNT_ACTIVE"
            }
        )
    
    # Actualizar o agregar descuento en el JSON
    if settings.category_discounts is None:
        settings.category_discounts = {}
    
    settings.category_discounts[data.category_id] = {
        "percentage": data.percentage,
        "name": data.name
    }
    
    # CRUCIAL: Marcar columna JSON como modificada para que SQLAlchemy la guarde
    attributes.flag_modified(settings, "category_discounts")
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    return {
        "success": True,
        "status_code": 200,
        "message": f"Descuento agregado a categoría {data.category_id}",
        "data": {
            "category_discounts": settings.category_discounts
        }
    }


@router.delete("/discount/category/{category_id}")
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
        attributes.flag_modified(settings, "category_discounts")
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        
        return {
            "success": True,
            "status_code": 200,
            "message": f"Descuento eliminado de categoría {category_id}",
            "data": {
                "category_discounts": settings.category_discounts
            }
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No existe descuento para la categoría {category_id}"
    )


@router.post("/discount/product")
async def add_product_discount(
    data: AddProductDiscount,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Agregar o actualizar descuento para un producto específico.
    No se puede agregar si hay un descuento global activo.
    """
    settings = get_or_create_settings(db)
    
    # Validar que no haya descuento global activo
    if settings.global_discount_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "status_code": 400,
                "message": "No se pueden agregar descuentos por producto mientras hay un descuento global activo. Desactiva el descuento global primero.",
                "error": "GLOBAL_DISCOUNT_ACTIVE"
            }
        )
    
    if settings.product_discounts is None:
        settings.product_discounts = {}
    
    settings.product_discounts[data.product_id] = {
        "percentage": data.percentage,
        "name": data.name
    }
    
    # CRUCIAL: Marcar columna JSON como modificada
    attributes.flag_modified(settings, "product_discounts")
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    return {
        "success": True,
        "status_code": 200,
        "message": f"Descuento agregado a producto {data.product_id}",
        "data": {
            "product_discounts": settings.product_discounts
        }
    }


@router.delete("/discount/product/{product_id}")
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
        attributes.flag_modified(settings, "product_discounts")
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        
        return {
            "success": True,
            "status_code": 200,
            "message": f"Descuento eliminado del producto {product_id}",
            "data": {
                "product_discounts": settings.product_discounts
            }
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No existe descuento para el producto {product_id}"
    )


@router.post("/seasonal-offer")
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
    attributes.flag_modified(settings, "seasonal_offers")
    settings.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(settings)
    
    return {
        "success": True,
        "status_code": 200,
        "message": f"Oferta temporal '{data.name}' creada exitosamente",
        "data": {
            "seasonal_offers": settings.seasonal_offers
        }
    }


@router.delete("/seasonal-offer/{offer_name}")
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
        original_count = len(settings.seasonal_offers)
        settings.seasonal_offers = [
            offer for offer in settings.seasonal_offers
            if offer.get("name") != offer_name
        ]
        
        if len(settings.seasonal_offers) < original_count:
            attributes.flag_modified(settings, "seasonal_offers")
            settings.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(settings)
            
            return {
                "success": True,
                "status_code": 200,
                "message": f"Oferta temporal '{offer_name}' eliminada exitosamente",
                "data": {
                    "seasonal_offers": settings.seasonal_offers
                }
            }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No existe la oferta temporal '{offer_name}'"
    )


@router.put("/user-registration")
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
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Configuración de registro actualizada exitosamente",
        "data": {
            "allow_user_registration": settings.allow_user_registration
        }
    }


@router.put("/max-items")
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
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Límite de productos por orden actualizado exitosamente",
        "data": {
            "max_items_per_order": settings.max_items_per_order
        }
    }


@router.get("/discounts/summary")
async def get_discounts_summary(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Obtener resumen de todos los descuentos activos.
    Muestra qué productos y categorías tienen descuentos aplicados.
    """
    from models.products import Product, Category
    
    settings = get_or_create_settings(db)
    
    # Obtener todas las categorías
    categories = db.query(Category).all()
    categories_list = []
    
    for cat in categories:
        cat_discount = None
        if settings.category_discounts and str(cat.id) in settings.category_discounts:
            cat_discount = settings.category_discounts[str(cat.id)]
        
        categories_list.append({
            "id": cat.id,
            "name": cat.name,
            "has_discount": cat_discount is not None,
            "discount": cat_discount
        })
    
    # Obtener todos los productos
    products = db.query(Product).filter(Product.is_active == True).all()
    products_list = []
    
    for prod in products:
        prod_discount = None
        if settings.product_discounts and str(prod.id) in settings.product_discounts:
            prod_discount = settings.product_discounts[str(prod.id)]
        
        products_list.append({
            "id": prod.id,
            "name": prod.name,
            "category_id": prod.category_id,
            "has_discount": prod_discount is not None,
            "discount": prod_discount
        })
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Resumen de descuentos obtenido exitosamente",
        "data": {
            "global_discount": {
                "enabled": settings.global_discount_enabled,
                "percentage": settings.global_discount_percentage if settings.global_discount_enabled else None,
                "name": settings.global_discount_name if settings.global_discount_enabled else None
            },
            "categories": categories_list,
            "products": products_list,
            "seasonal_offers": settings.seasonal_offers,
            "summary": {
                "total_categories": len(categories_list),
                "categories_with_discount": len([c for c in categories_list if c["has_discount"]]),
                "total_products": len(products_list),
                "products_with_discount": len([p for p in products_list if p["has_discount"]])
            }
        }
    }
