"""
Rutas públicas para configuraciones del sistema.
Accesibles sin autenticación.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from models.admin_settings import AdminSettings
from core.discount_service import get_shipping_price

router = APIRouter(prefix="/settings", tags=["Public Settings"])


def get_settings(db: Session) -> Optional[AdminSettings]:
    """Obtener configuraciones (helper)"""
    return db.query(AdminSettings).first()


@router.get("/public")
async def get_public_settings(db: Session = Depends(get_db)):
    """
    Obtener configuraciones públicas visibles para todos los usuarios.
    Incluye: mensajes de mantenimiento, ofertas activas, registro habilitado.
    """
    settings = get_settings(db)
    
    if not settings:
        return {
            "success": True,
            "status_code": 200,
            "message": "No hay configuraciones disponibles",
            "data": {
                "maintenance_mode": False,
                "maintenance_message": None,
                "allow_user_registration": True,
                "active_offers": []
            }
        }
    
    # Filtrar solo ofertas activas por fecha
    from datetime import datetime
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    active_offers = []
    if settings.seasonal_offers:
        for offer in settings.seasonal_offers:
            start = offer.get('start_date', '')
            end = offer.get('end_date', '')
            
            if start and end and start <= today <= end:
                active_offers.append({
                    "name": offer.get('name'),
                    "discount_percentage": offer.get('discount_percentage'),
                    "end_date": end
                })
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Configuraciones públicas obtenidas",
        "data": {
            "maintenance_mode": settings.maintenance_mode,
            "maintenance_message": settings.maintenance_message if settings.maintenance_mode else None,
            "allow_user_registration": settings.allow_user_registration,
            "active_offers": active_offers,
            "has_global_discount": settings.global_discount_enabled,
            "global_discount_name": settings.global_discount_name if settings.global_discount_enabled else None
        }
    }


@router.get("/shipping/calculate")
async def calculate_shipping(
    total: float = Query(..., ge=0, description="Total de la orden"),
    db: Session = Depends(get_db)
):
    """
    Calcular costo de envío según el total de la orden.
    Muestra si califica para envío gratis.
    """
    shipping_info = get_shipping_price(db, total)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Costo de envío calculado",
        "data": shipping_info
    }


@router.get("/shipping/info")
async def get_shipping_info(db: Session = Depends(get_db)):
    """
    Obtener información de envío sin calcular.
    Útil para mostrar al usuario antes de que agregue productos.
    """
    settings = get_settings(db)
    
    if not settings:
        return {
            "success": True,
            "status_code": 200,
            "data": {
                "shipping_price": 0.0,
                "free_shipping_threshold": None,
                "message": "Información de envío no disponible"
            }
        }
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Información de envío obtenida",
        "data": {
            "shipping_price": settings.shipping_price,
            "free_shipping_threshold": settings.free_shipping_threshold,
            "message": f"Envío ${settings.shipping_price}" + (
                f" (gratis en compras mayores a ${settings.free_shipping_threshold})" 
                if settings.free_shipping_threshold 
                else ""
            )
        }
    }
