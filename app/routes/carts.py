"""
Endpoints para gestión de carritos de compra usando Redis.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict
from core.database import get_db
from core.dependencies import get_current_user
from core.redis_service import CartService
from models.user import User
from models.products import Product
from models.protocols import Protocol
from schemas.carts import (
    CartItemCreate,
    CartItemUpdate,
    CartItemType,
    CartSummary
)

router = APIRouter(
    prefix="/cart",
    tags=["cart"]
)


def get_products_data(product_ids: List[int], db: Session) -> Dict[int, Product]:
    """
    Obtener información de productos desde PostgreSQL.
    """
    if not product_ids:
        return {}
    
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.is_active == True
    ).all()
    
    return {product.id: product for product in products}


def format_cart_response(user_id: str, db: Session) -> dict:
    """
    Formatear respuesta del carrito desde Redis.
    Aplica descuentos activos a los productos y calcula envío.
    """
    # Obtener carrito desde Redis
    cart_data = CartService.get_cart(user_id)
    
    if not cart_data:
        return {
            "user_id": user_id,
            "items": [],
            "total_items": 0,
            "total_amount": 0.0,
            "total_discount": 0.0,
            "total_without_discount": 0.0,
            "shipping_cost": 0.0,
            "grand_total": 0.0,
            "shipping_info": {
                "shipping_price": 0.0,
                "is_free": True,
                "message": "Carrito vacío"
            }
        }
    
    # Separar IDs por tipo de item
    product_ids = [it["id"] for it in cart_data.values() if it["item_type"] == "product"]
    protocol_ids = [it["id"] for it in cart_data.values() if it["item_type"] == "protocol"]
    products = get_products_data(product_ids, db)
    protocols = {
        p.id: p for p in db.query(Protocol).filter(
            Protocol.id.in_(protocol_ids),
            Protocol.is_published == True
        ).all()
    } if protocol_ids else {}

    # Aplicar descuentos a los productos
    from core.discount_service import calculate_product_discount, get_shipping_price
    from models.admin_settings import AdminSettings

    settings = db.query(AdminSettings).first()

    # Construir items con información completa
    items = []
    total_items = 0
    total_amount = 0.0
    total_discount = 0.0
    total_without_discount = 0.0
    category_ids = []
    has_physical_item = False

    for cart_item in cart_data.values():
        item_type = cart_item["item_type"]
        item_id = cart_item["id"]
        quantity = cart_item["quantity"]

        # ---------- PROTOCOLOS (digitales, sin envío, sin descuentos, sin stock) ----------
        if item_type == "protocol":
            protocol = protocols.get(item_id)
            if not protocol:
                continue  # protocolo inexistente o despublicado: se omite

            price = float(protocol.price)
            subtotal = round(price * quantity, 2)
            items.append({
                "item_type": "protocol",
                "protocol_id": protocol.id,
                "product_id": None,
                "quantity": quantity,
                "product": {
                    "id": protocol.id,
                    "name": protocol.name,
                    "slug": protocol.slug,
                    "price": price,
                    "original_price": price,
                    "stock": None,
                    "category_id": protocol.category_id,
                    "image_url": protocol.image_url,
                    "is_active": protocol.is_published,
                    "is_digital": True,
                    "has_discount": False,
                    "discount": None,
                },
                "subtotal": subtotal,
                "subtotal_without_discount": subtotal,
                "discount_amount": 0.0,
            })
            total_items += quantity
            total_amount += subtotal
            total_without_discount += subtotal
            continue

        # ---------- PRODUCTOS ----------
        product = products.get(item_id)
        if not product:
            continue  # producto inactivo/inexistente: se omite

        # Solo los productos físicos cuentan para el cálculo de envío
        if not product.is_digital:
            has_physical_item = True
            if product.category_id and product.category_id not in category_ids:
                category_ids.append(product.category_id)

        original_price = float(product.price)

        # Calcular descuento si hay configuración de admin
        if settings:
            final_price, discount_info = calculate_product_discount(product, settings)
        else:
            final_price = original_price
            discount_info = None

        # Calcular subtotales
        subtotal = round(final_price * quantity, 2)
        subtotal_without_discount = round(original_price * quantity, 2)
        item_discount = round(subtotal_without_discount - subtotal, 2)

        items.append({
            "item_type": "product",
            "product_id": product.id,
            "protocol_id": None,
            "quantity": quantity,
            "product": {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "price": final_price,
                "original_price": original_price,
                "stock": product.stock,
                "category_id": product.category_id,
                "image_url": product.image_url,
                "is_active": product.is_active,
                "is_digital": product.is_digital,
                "has_discount": discount_info is not None,
                "discount": discount_info
            },
            "subtotal": subtotal,
            "subtotal_without_discount": subtotal_without_discount,
            "discount_amount": item_discount
        })

        total_items += quantity
        total_amount += subtotal
        total_discount += item_discount
        total_without_discount += subtotal_without_discount

    # Calcular envío: solo si hay al menos un producto físico
    if not has_physical_item:
        shipping_info = {
            "shipping_price": 0.0,
            "is_free": True,
            "message": "Entrega digital — sin costo de envío"
        }
        shipping_cost = 0.0
    else:
        shipping_info = get_shipping_price(db, total_amount, category_ids)
        shipping_cost = shipping_info.get("shipping_price", 0.0)
    grand_total = round(total_amount + shipping_cost, 2)
    
    return {
        "user_id": user_id,
        "items": items,
        "total_items": total_items,
        "total_amount": round(total_amount, 2),  # Total con descuentos (sin envío)
        "total_discount": round(total_discount, 2),  # Total ahorrado
        "total_without_discount": round(total_without_discount, 2),  # Total original
        "shipping_cost": shipping_cost,  # Costo de envío
        "grand_total": grand_total,  # Total final incluyendo envío
        "shipping_info": shipping_info  # Información detallada de envío
    }


# ==================== ENDPOINTS ====================

@router.get("", include_in_schema=True)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener el carrito del usuario desde Redis.
    
    - Retorna el carrito con todos sus items
    - Incluye información completa de cada producto desde PostgreSQL
    - Calcula totales automáticamente
    """
    user_id = str(current_user.id)
    cart_data = format_cart_response(user_id, db)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Carrito obtenido exitosamente",
        "data": cart_data
    }


@router.get("/summary")
async def get_cart_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener resumen del carrito (solo totales).
    
    Útil para mostrar el badge del carrito sin cargar todos los items.
    """
    user_id = str(current_user.id)
    cart_data = format_cart_response(user_id, db)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Resumen del carrito",
        "data": {
            "total_items": cart_data["total_items"],
            "total_amount": cart_data["total_amount"],
            "shipping_cost": cart_data["shipping_cost"],
            "grand_total": cart_data["grand_total"]
        }
    }


@router.post("/items", status_code=201)
async def add_item_to_cart(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Agregar un item al carrito en Redis (producto o protocolo).

    - Productos: valida existencia, estado activo y stock suficiente.
    - Protocolos: valida que exista y esté publicado. Sin stock, cantidad fija = 1
      (un protocolo es un acceso, no tiene sentido comprarlo varias veces).
    - Si el item ya existe en el carrito, incrementa la cantidad (productos).
    """
    user_id = str(current_user.id)
    cart_data = CartService.get_cart(user_id)

    # ---------- PROTOCOLO ----------
    if item_data.item_type == CartItemType.PROTOCOL:
        protocol = db.query(Protocol).filter(
            Protocol.id == item_data.protocol_id,
            Protocol.is_published == True
        ).first()
        if not protocol:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "status_code": 404,
                    "message": "Protocolo no encontrado o no disponible",
                    "error": "PROTOCOL_NOT_FOUND"
                }
            )

        # Evitar recomprar un protocolo al que ya tiene acceso
        from models.protocols import ProtocolAccess
        already_owns = db.query(ProtocolAccess).filter(
            ProtocolAccess.protocol_id == protocol.id,
            ProtocolAccess.user_id == current_user.id,
            ProtocolAccess.is_active == True
        ).first()
        if already_owns:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": "Ya tienes acceso a este protocolo",
                    "error": "PROTOCOL_ALREADY_OWNED"
                }
            )

        # Cantidad fija = 1 (no se debe incrementar si ya está en el carrito)
        protocol_key = f"protocol:{protocol.id}"
        if protocol_key in cart_data:
            CartService.update_item_quantity(user_id, protocol.id, 1, item_type="protocol")
        else:
            CartService.add_item(user_id, protocol.id, 1, item_type="protocol")

        cart_response = format_cart_response(user_id, db)
        return {
            "success": True,
            "status_code": 201,
            "message": "Protocolo agregado al carrito",
            "data": cart_response
        }

    # ---------- PRODUCTO ----------
    product = db.query(Product).filter(
        Product.id == item_data.product_id,
        Product.is_active == True
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado o no disponible",
                "error": "PRODUCT_NOT_FOUND"
            }
        )

    # Calcular nueva cantidad
    entry_key = f"product:{item_data.product_id}"
    current_quantity = cart_data.get(entry_key, {}).get("quantity", 0)
    new_quantity = current_quantity + item_data.quantity

    # Validar stock (los productos digitales no tienen límite de stock)
    if not product.is_digital and new_quantity > product.stock:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"Stock insuficiente. Disponible: {product.stock}",
                "error": "INSUFFICIENT_STOCK"
            }
        )

    # Agregar al carrito en Redis
    CartService.add_item(user_id, item_data.product_id, item_data.quantity, item_type="product")

    # Retornar carrito actualizado
    cart_response = format_cart_response(user_id, db)
    message = "Cantidad actualizada en el carrito" if current_quantity > 0 else "Producto agregado al carrito"

    return {
        "success": True,
        "status_code": 201,
        "message": message,
        "data": cart_response
    }


@router.put("/items/{item_id}")
async def update_cart_item(
    item_id: int,
    item_data: CartItemUpdate,
    item_type: CartItemType = Query(CartItemType.PRODUCT, description="Tipo de item: product | protocol"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar cantidad de un item del carrito en Redis.

    - Productos: valida existencia, estado activo y stock disponible.
    - Protocolos: la cantidad siempre es 1 (es un acceso).
    """
    user_id = str(current_user.id)
    cart_data = CartService.get_cart(user_id)
    entry_key = f"{item_type.value}:{item_id}"

    if entry_key not in cart_data:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Item no encontrado en el carrito",
                "error": "ITEM_NOT_FOUND"
            }
        )

    # Los protocolos no permiten cambiar la cantidad (siempre 1)
    if item_type == CartItemType.PROTOCOL:
        CartService.update_item_quantity(user_id, item_id, 1, item_type="protocol")
        return {
            "success": True,
            "status_code": 200,
            "message": "Cantidad actualizada",
            "data": format_cart_response(user_id, db)
        }

    # Validar que el producto exista y esté activo
    product = db.query(Product).filter(
        Product.id == item_id,
        Product.is_active == True
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado o no disponible",
                "error": "PRODUCT_NOT_FOUND"
            }
        )

    # Validar stock (los productos digitales no tienen límite de stock)
    if not product.is_digital and item_data.quantity > product.stock:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"Stock insuficiente. Disponible: {product.stock}",
                "error": "INSUFFICIENT_STOCK"
            }
        )

    # Actualizar cantidad en Redis
    CartService.update_item_quantity(user_id, item_id, item_data.quantity, item_type="product")

    return {
        "success": True,
        "status_code": 200,
        "message": "Cantidad actualizada",
        "data": format_cart_response(user_id, db)
    }


@router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: int,
    item_type: CartItemType = Query(CartItemType.PRODUCT, description="Tipo de item: product | protocol"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar un item del carrito en Redis (producto o protocolo).
    """
    user_id = str(current_user.id)
    cart_data = CartService.get_cart(user_id)
    entry_key = f"{item_type.value}:{item_id}"

    if entry_key not in cart_data:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Item no encontrado en el carrito",
                "error": "ITEM_NOT_FOUND"
            }
        )

    CartService.remove_item(user_id, item_id, item_type=item_type.value)

    return {
        "success": True,
        "status_code": 200,
        "message": "Item eliminado del carrito",
        "data": format_cart_response(user_id, db)
    }


@router.delete("/clear")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Vaciar el carrito completamente en Redis.
    """
    user_id = str(current_user.id)
    
    # Limpiar carrito en Redis
    CartService.clear_cart(user_id)
    
    # Retornar carrito vacío
    cart_response = format_cart_response(user_id, db)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Carrito vaciado exitosamente",
        "data": cart_response
    }
