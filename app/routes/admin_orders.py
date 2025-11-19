"""
Endpoints de administración para órdenes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, cast, Date
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from core.database import get_db
from core.dependencies import get_current_user
from models.user import User
from models.order import Order, OrderItem, OrderStatus, PaymentMethod
from models.addresses import Address
from models.products import Product
from schemas.orders import (
    OrderStatusUpdate,
    OrderAdminResponse,
    OrderStatsResponse
)

router = APIRouter(
    prefix="/admin/orders",
    tags=["admin-orders"]
)


# ==================== MIDDLEWARE ====================

def verify_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verificar que el usuario sea administrador"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "status_code": 403,
                "message": "No tienes permisos de administrador",
                "error": "FORBIDDEN"
            }
        )
    return current_user


def format_order_admin_response(order: Order, db: Session) -> dict:
    """Formatear orden para respuesta de admin (con más detalles)"""
    # Obtener items
    items = []
    for item in order.order_items:
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "product_sku": item.product_sku,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "subtotal": float(item.subtotal)
        })
    
    # Obtener dirección completa
    address = db.query(Address).filter(Address.id == order.address_id).first()
    shipping_address = None
    if address:
        shipping_address = {
            "id": address.id,
            "full_name": address.full_name,
            "phone": address.phone,
            "rfc": address.rfc,
            "label": address.label,
            "street": address.street,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country
        }
    
    # Obtener información del usuario
    user = db.query(User).filter(User.id == order.user_id).first()
    user_email = user.email if user else None
    user_name = user.full_name if user else None
    
    return {
        "id": order.id,
        "user_id": str(order.user_id),
        "user_email": user_email,
        "user_name": user_name,
        "address_id": order.address_id,
        "shipping_address": shipping_address,
        "payment_method": order.payment_method.value,
        "payment_id": order.payment_id,
        "payment_status": order.payment_status,
        "status": order.status.value,
        "subtotal": float(order.subtotal),
        "shipping_cost": float(order.shipping_cost),
        "tax": float(order.tax),
        "total": float(order.total),
        "notes": order.notes,
        "admin_notes": order.admin_notes,
        "tracking_number": order.tracking_number,
        "order_items": items,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
    }


# ==================== ENDPOINTS ====================

@router.get("/")
async def get_all_orders(
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    payment_method: Optional[str] = Query(None, description="Filtrar por método de pago"),
    user_email: Optional[str] = Query(None, description="Filtrar por email de usuario"),
    date_from: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Buscar por ID de orden o email")
):
    """
    Obtener todas las órdenes (admin).
    
    - Soporte de filtros múltiples
    - Paginación
    - Búsqueda por ID o email
    """
    query = db.query(Order)
    
    # Filtro por estado
    if status:
        try:
            query = query.filter(Order.status == OrderStatus(status))
        except ValueError:
            pass
    
    # Filtro por método de pago
    if payment_method:
        try:
            query = query.filter(Order.payment_method == PaymentMethod(payment_method))
        except ValueError:
            pass
    
    # Filtro por email de usuario
    if user_email:
        user = db.query(User).filter(User.email.ilike(f"%{user_email}%")).first()
        if user:
            query = query.filter(Order.user_id == user.id)
    
    # Filtro por rango de fechas
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Order.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Order.created_at < date_to_obj)
        except ValueError:
            pass
    
    # Búsqueda general
    if search:
        if search.isdigit():
            query = query.filter(Order.id == int(search))
        else:
            user = db.query(User).filter(User.email.ilike(f"%{search}%")).first()
            if user:
                query = query.filter(Order.user_id == user.id)
    
    # Contar total
    total = query.count()
    
    # Obtener órdenes con paginación
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    # Formatear respuesta
    orders_list = []
    for order in orders:
        items_count = len(order.order_items)
        user = db.query(User).filter(User.id == order.user_id).first()
        
        orders_list.append({
            "id": order.id,
            "user_email": user.email if user else None,
            "user_name": user.full_name if user else None,
            "status": order.status.value,
            "payment_method": order.payment_method.value,
            "total": float(order.total),
            "items_count": items_count,
            "created_at": order.created_at.isoformat() if order.created_at else None
        })
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Órdenes obtenidas exitosamente",
        "data": {
            "orders": orders_list,
            "total": total,
            "page": skip // limit + 1 if limit > 0 else 1,
            "page_size": limit
        }
    }


@router.get("/{order_id}")
async def get_order_admin(
    order_id: int,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Obtener detalle completo de una orden (admin).
    
    - Incluye información de usuario y dirección
    - Incluye notas internas
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Orden no encontrada",
                "error": "ORDER_NOT_FOUND"
            }
        )
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Orden obtenida exitosamente",
        "data": format_order_admin_response(order, db)
    }


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Actualizar estado de una orden (admin).
    
    - Actualiza timestamps según el estado
    - Permite agregar notas internas
    - Permite agregar número de guía
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Orden no encontrada",
                "error": "ORDER_NOT_FOUND"
            }
        )
    
    # Actualizar estado
    old_status = order.status
    new_status = OrderStatus(status_data.status)
    order.status = new_status
    order.updated_at = datetime.now()
    
    # Actualizar timestamps según el nuevo estado
    if new_status == OrderStatus.PAID and not order.paid_at:
        order.paid_at = datetime.now()
    elif new_status == OrderStatus.SHIPPED and not order.shipped_at:
        order.shipped_at = datetime.now()
    elif new_status == OrderStatus.DELIVERED and not order.delivered_at:
        order.delivered_at = datetime.now()
    
    # Actualizar notas y tracking
    if status_data.admin_notes:
        order.admin_notes = status_data.admin_notes
    
    if status_data.tracking_number:
        order.tracking_number = status_data.tracking_number
    
    db.commit()
    db.refresh(order)
    
    return {
        "success": True,
        "status_code": 200,
        "message": f"Estado actualizado de '{old_status.value}' a '{new_status.value}'",
        "data": format_order_admin_response(order, db)
    }


@router.get("/stats/summary")
async def get_order_stats(
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de órdenes y ganancias (admin).
    
    - Total de órdenes por estado
    - Ganancias por período (hoy, semana, mes, año)
    - Top productos vendidos
    """
    # Contar órdenes por estado
    total_orders = db.query(func.count(Order.id)).scalar()
    pending_orders = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.PENDING).scalar()
    processing_orders = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.PROCESSING).scalar()
    shipped_orders = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.SHIPPED).scalar()
    delivered_orders = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.DELIVERED).scalar()
    cancelled_orders = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.CANCELLED).scalar()
    
    # Calcular ganancias totales (solo órdenes pagadas o entregadas)
    revenue_query = db.query(func.sum(Order.total)).filter(
        Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
    )
    total_revenue = revenue_query.scalar() or Decimal("0.00")
    
    # Ganancias de hoy
    today = datetime.now().date()
    revenue_today = db.query(func.sum(Order.total)).filter(
        and_(
            cast(Order.created_at, Date) == today,
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
        )
    ).scalar() or Decimal("0.00")
    
    # Ganancias de esta semana
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    revenue_this_week = db.query(func.sum(Order.total)).filter(
        and_(
            Order.created_at >= week_start,
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
        )
    ).scalar() or Decimal("0.00")
    
    # Ganancias de este mes
    month_start = datetime.now().replace(day=1)
    revenue_this_month = db.query(func.sum(Order.total)).filter(
        and_(
            Order.created_at >= month_start,
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
        )
    ).scalar() or Decimal("0.00")
    
    # Ganancias de este año
    year_start = datetime.now().replace(month=1, day=1)
    revenue_this_year = db.query(func.sum(Order.total)).filter(
        and_(
            Order.created_at >= year_start,
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
        )
    ).scalar() or Decimal("0.00")
    
    # Top 5 productos más vendidos
    top_products_query = db.query(
        Product.id,
        Product.name,
        Product.sku,
        func.sum(OrderItem.quantity).label("total_sold"),
        func.sum(OrderItem.subtotal).label("total_revenue")
    ).join(
        OrderItem, Product.id == OrderItem.product_id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
    ).group_by(
        Product.id, Product.name, Product.sku
    ).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(5).all()
    
    top_products = []
    for product in top_products_query:
        top_products.append({
            "product_id": product.id,
            "product_name": product.name,
            "product_sku": product.sku,
            "total_sold": int(product.total_sold),
            "total_revenue": float(product.total_revenue)
        })
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Estadísticas obtenidas exitosamente",
        "data": {
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "pending_orders": pending_orders,
            "processing_orders": processing_orders,
            "shipped_orders": shipped_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "revenue_today": float(revenue_today),
            "revenue_this_week": float(revenue_this_week),
            "revenue_this_month": float(revenue_this_month),
            "revenue_this_year": float(revenue_this_year),
            "top_products": top_products
        }
    }


@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Eliminar una orden (admin).
    
    - Solo para casos excepcionales
    - Restaura el stock de los productos
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Orden no encontrada",
                "error": "ORDER_NOT_FOUND"
            }
        )
    
    # Restaurar stock si la orden no fue cancelada
    if order.status != OrderStatus.CANCELLED:
        for item in order.order_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
    
    # Eliminar orden (cascade eliminará los items)
    db.delete(order)
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Orden eliminada exitosamente",
        "data": None
    }
