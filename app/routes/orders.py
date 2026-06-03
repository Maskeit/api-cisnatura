"""
Endpoints para órdenes de compra (usuarios).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
from decimal import Decimal

from core.database import get_db
from core.dependencies import get_current_user
from core.redis_service import CartService
from models.user import User
from models.order import Order, OrderItem, OrderStatus, PaymentMethod
from models.addresses import Address
from models.products import Product
from schemas.orders import (
    OrderCreate,
    OrderResponse,
    OrderListItem,
    OrderItemResponse
)

router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)


def format_order_response(order: Order, db: Session) -> dict:
    """Formatear orden para respuesta"""
    # Obtener items de la orden
    items = []
    for item in order.order_items:
        items.append({
            "id": item.id,
            "item_type": item.item_type,
            "product_id": item.product_id,
            "protocol_id": item.protocol_id,
            "product_name": item.product_name,
            "product_sku": item.product_sku,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "subtotal": float(item.subtotal)
        })
    
    return {
        "id": order.id,
        "user_id": str(order.user_id),
        "address_id": order.address_id,
        "payment_method": order.payment_method.value,
        "payment_id": order.payment_id,
        "payment_status": order.payment_status,
        "status": order.status.value,
        "subtotal": float(order.subtotal),
        "shipping_cost": float(order.shipping_cost),
        "tax": float(order.tax),
        "total": float(order.total),
        "notes": order.notes,
        "tracking_number": order.tracking_number,
        "order_items": items,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
    }


# ==================== ENDPOINTS ====================

@router.post("/", status_code=201)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear orden desde el carrito.
    
    - Valida que el carrito no esté vacío
    - Valida que la dirección pertenezca al usuario
    - Valida stock de productos
    - Crea la orden con snapshot de productos
    - Limpia el carrito de Redis
    """
    # Obtener carrito de Redis
    cart_service = CartService()
    cart_data = cart_service.get_cart(str(current_user.id))
    
    if not cart_data:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El carrito está vacío",
                "error": "EMPTY_CART"
            }
        )
    
    # Validar items y calcular totales primero (para saber si la orden es digital)
    from models.protocols import Protocol
    order_items_data = []
    subtotal = Decimal("0.00")
    category_ids = []
    all_digital = True  # Se asume digital hasta que se encuentre un producto físico

    for cart_item in cart_data.values():
        item_type = cart_item["item_type"]
        item_id = cart_item["id"]
        quantity = cart_item["quantity"]

        # ---------- PROTOCOLO (digital: sin stock, sin envío) ----------
        if item_type == "protocol":
            protocol = db.query(Protocol).filter(
                Protocol.id == item_id,
                Protocol.is_published == True
            ).first()
            if not protocol:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "status_code": 404,
                        "message": f"Protocolo {item_id} no encontrado o no disponible",
                        "error": "PROTOCOL_NOT_FOUND"
                    }
                )
            item_subtotal = Decimal(str(protocol.price)) * quantity
            subtotal += item_subtotal
            order_items_data.append({
                "item_type": "protocol",
                "product_id": None,
                "protocol_id": protocol.id,
                "product_name": protocol.name,
                "product_sku": None,
                "quantity": quantity,
                "unit_price": Decimal(str(protocol.price)),
                "subtotal": item_subtotal,
                "is_digital": True,
            })
            continue

        # ---------- PRODUCTO ----------
        product = db.query(Product).filter(Product.id == item_id).first()
        if not product:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "status_code": 404,
                    "message": f"Producto {item_id} no encontrado",
                    "error": "PRODUCT_NOT_FOUND"
                }
            )

        if not product.is_digital:
            all_digital = False
            # Validar stock solo para productos físicos
            if product.stock < quantity:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "status_code": 400,
                        "message": f"Stock insuficiente para {product.name}. Disponible: {product.stock}",
                        "error": "INSUFFICIENT_STOCK"
                    }
                )
            if product.category_id not in category_ids:
                category_ids.append(product.category_id)

        # Calcular subtotal del item
        item_subtotal = Decimal(str(product.price)) * quantity
        subtotal += item_subtotal

        order_items_data.append({
            "item_type": "product",
            "product_id": product.id,
            "protocol_id": None,
            "product_name": product.name,
            "product_sku": product.sku,
            "quantity": quantity,
            "unit_price": Decimal(str(product.price)),
            "subtotal": item_subtotal,
            "is_digital": product.is_digital
        })
    
    # Validar dirección solo si hay productos físicos en la orden
    address_id = None
    if not all_digital:
        if not order_data.address_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": "Se requiere dirección de envío para productos físicos",
                    "error": "ADDRESS_REQUIRED"
                }
            )
        address = db.query(Address).filter(
            Address.id == order_data.address_id,
            Address.user_id == current_user.id
        ).first()
        if not address:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "status_code": 404,
                    "message": "Dirección no encontrada",
                    "error": "ADDRESS_NOT_FOUND"
                }
            )
        address_id = order_data.address_id
    
    # Calcular costo de envío (solo para productos físicos)
    from core.discount_service import get_shipping_price
    if all_digital:
        shipping_cost = Decimal("0.00")
    else:
        shipping_info = get_shipping_price(db, float(subtotal), category_ids)
        shipping_cost = Decimal(str(shipping_info["shipping_price"]))
    total = subtotal + shipping_cost
    
    # Crear orden en estado PENDING (esperando que se abra el checkout)
    new_order = Order(
        user_id=current_user.id,
        address_id=address_id,
        payment_method=PaymentMethod(order_data.payment_method),
        status=OrderStatus.PENDING,  # PENDING = orden creada pero no se abrió checkout
        payment_status="awaiting_checkout",  # Indica que falta abrir el checkout
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=Decimal("0.00"),  # Los productos ya incluyen impuestos
        total=total,
        notes=order_data.notes
    )
    
    db.add(new_order)
    db.flush()  # Para obtener el ID de la orden
    
    # Crear items de la orden
    for item_data in order_items_data:
        is_digital = item_data.pop("is_digital")  # Sacar antes de crear OrderItem
        order_item = OrderItem(
            order_id=new_order.id,
            **item_data
        )
        db.add(order_item)
        
        # Reducir stock solo para productos físicos
        if not is_digital:
            product = db.query(Product).filter(Product.id == item_data["product_id"]).first()
            product.stock -= item_data["quantity"]
    
    db.commit()
    db.refresh(new_order)
    
    # NO limpiar el carrito todavía - se limpiará cuando el webhook confirme el pago
    # cart_service.clear_cart(str(current_user.id))
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Orden creada - Procede al pago para confirmar",
        "data": format_order_response(new_order, db)
    }


@router.get("/")
async def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """
    Obtener todas las órdenes del usuario autenticado.
    
    - Ordenadas por fecha de creación (más recientes primero)
    - Paginadas
    """
    # Obtener órdenes del usuario
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(
        Order.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    # Contar total de órdenes
    total = db.query(func.count(Order.id)).filter(
        Order.user_id == current_user.id
    ).scalar()
    
    # Formatear respuesta simplificada
    orders_list = []
    for order in orders:
        items_count = db.query(func.count(OrderItem.id)).filter(
            OrderItem.order_id == order.id
        ).scalar()
        
        orders_list.append({
            "id": order.id,
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
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener detalle de una orden específica.
    
    - Solo se puede ver si pertenece al usuario autenticado
    - Incluye todos los items y detalles
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
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
        "data": format_order_response(order, db)
    }


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancelar una orden.
    
    - Solo se puede cancelar si está en estado 'pending' o 'payment_pending'
    - Restaura el stock de los productos
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
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
    
    # Validar que se pueda cancelar
    if order.status not in [OrderStatus.PENDING, OrderStatus.PAYMENT_PENDING]:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"No se puede cancelar una orden en estado '{order.status.value}'",
                "error": "CANNOT_CANCEL_ORDER"
            }
        )
    
    # Restaurar stock
    for item in order.order_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity
    
    # Actualizar estado
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.now()
    
    db.commit()
    db.refresh(order)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Orden cancelada exitosamente",
        "data": format_order_response(order, db)
    }
