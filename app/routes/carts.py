"""
Endpoints para gestión de carritos de compra usando Redis.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from core.database import get_db
from core.dependencies import get_current_user
from core.redis_service import CartService
from models.user import User
from models.products import Product
from schemas.carts import (
    CartItemCreate,
    CartItemUpdate,
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
    
    # Obtener IDs de productos
    product_ids = [int(pid) for pid in cart_data.keys()]
    products = get_products_data(product_ids, db)
    
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
    
    for product_id_str, cart_item in cart_data.items():
        product_id = int(product_id_str)
        product = products.get(product_id)
        
        # Solo incluir productos activos
        if not product:
            continue
        
        # Recolectar category_ids para cálculo de envío
        if product.category_id and product.category_id not in category_ids:
            category_ids.append(product.category_id)
        
        quantity = cart_item["quantity"]
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
            "product_id": product_id,
            "quantity": quantity,
            "product": {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "price": final_price,  # Precio con descuento aplicado
                "original_price": original_price,  # Precio original
                "stock": product.stock,
                "category_id": product.category_id,
                "image_url": product.image_url,
                "is_active": product.is_active,
                "has_discount": discount_info is not None,
                "discount": discount_info  # Info del descuento aplicado
            },
            "subtotal": subtotal,  # Subtotal con descuento
            "subtotal_without_discount": subtotal_without_discount,  # Subtotal sin descuento
            "discount_amount": item_discount  # Ahorro por item
        })
        
        total_items += quantity
        total_amount += subtotal
        total_discount += item_discount
        total_without_discount += subtotal_without_discount
    
    # Calcular costo de envío basado en categorías y total
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
    Agregar producto al carrito en Redis.
    
    - Si el producto ya existe, incrementa la cantidad
    - Valida que el producto exista y esté activo
    - Valida que haya stock suficiente
    """
    user_id = str(current_user.id)
    
    # Validar que el producto exista y esté activo
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
    
    # Obtener carrito actual desde Redis
    cart_data = CartService.get_cart(user_id)
    product_id_str = str(item_data.product_id)
    
    # Calcular nueva cantidad
    current_quantity = cart_data.get(product_id_str, {}).get("quantity", 0)
    new_quantity = current_quantity + item_data.quantity
    
    # Validar stock
    if new_quantity > product.stock:
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
    CartService.add_item(user_id, item_data.product_id, item_data.quantity)
    
    # Retornar carrito actualizado
    cart_response = format_cart_response(user_id, db)
    message = "Cantidad actualizada en el carrito" if current_quantity > 0 else "Producto agregado al carrito"
    
    return {
        "success": True,
        "status_code": 201,
        "message": message,
        "data": cart_response
    }


@router.put("/items/{product_id}")
async def update_cart_item(
    product_id: int,
    item_data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar cantidad de un item del carrito en Redis.
    
    - Permite aumentar o disminuir la cantidad
    - Valida que el producto exista en el carrito
    - Valida stock disponible
    """
    user_id = str(current_user.id)
    
    # Verificar que el producto esté en el carrito
    cart_data = CartService.get_cart(user_id)
    product_id_str = str(product_id)
    
    if product_id_str not in cart_data:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado en el carrito",
                "error": "ITEM_NOT_FOUND"
            }
        )
    
    # Validar que el producto exista y esté activo
    product = db.query(Product).filter(
        Product.id == product_id,
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
    
    # Validar stock
    if item_data.quantity > product.stock:
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
    CartService.update_item_quantity(user_id, product_id, item_data.quantity)
    
    # Retornar carrito actualizado
    cart_response = format_cart_response(user_id, db)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Cantidad actualizada",
        "data": cart_response
    }


@router.delete("/items/{product_id}")
async def remove_cart_item(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar un item del carrito en Redis.
    """
    user_id = str(current_user.id)
    
    # Verificar que el producto esté en el carrito
    cart_data = CartService.get_cart(user_id)
    product_id_str = str(product_id)
    
    if product_id_str not in cart_data:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado en el carrito",
                "error": "ITEM_NOT_FOUND"
            }
        )
    
    # Eliminar item de Redis
    CartService.remove_item(user_id, product_id)
    
    # Retornar carrito actualizado
    cart_response = format_cart_response(user_id, db)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Producto eliminado del carrito",
        "data": cart_response
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
