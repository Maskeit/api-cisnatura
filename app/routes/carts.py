"""
Endpoints para gestión de carritos de compra.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from core.database import get_db
from core.dependencies import get_current_user
from models.user import User
from models.carts import Cart, CartItem
from models.products import Product
from schemas.carts import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartResponse,
    CartSummary
)

router = APIRouter(
    prefix="/cart",
    tags=["cart"]
)


def get_or_create_cart(user_id: str, db: Session) -> Cart:
    """
    Obtener carrito activo del usuario o crear uno nuevo.
    """
    cart = db.query(Cart).filter(
        Cart.user_id == user_id,
        Cart.is_active == True
    ).first()
    
    if not cart:
        cart = Cart(user_id=user_id, is_active=True)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    return cart


def calculate_cart_totals(cart: Cart) -> dict:
    """
    Calcular totales del carrito.
    """
    total_items = sum(item.quantity for item in cart.cart_items)
    total_amount = sum(
        float(item.product.price) * item.quantity 
        for item in cart.cart_items
        if item.product.is_active
    )
    
    return {
        "total_items": total_items,
        "total_amount": round(total_amount, 2)
    }


def format_cart_response(cart: Cart) -> dict:
    """
    Formatear respuesta del carrito con todos los datos.
    """
    totals = calculate_cart_totals(cart)
    
    items = []
    for item in cart.cart_items:
        # Solo mostrar productos activos
        if not item.product.is_active:
            continue
            
        items.append({
            "id": item.id,
            "cart_id": item.cart_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "product": {
                "id": item.product.id,
                "name": item.product.name,
                "slug": item.product.slug,
                "price": float(item.product.price),
                "stock": item.product.stock,
                "image_url": item.product.image_url,
                "is_active": item.product.is_active
            },
            "subtotal": round(float(item.product.price) * item.quantity, 2),
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None
        })
    
    return {
        "id": cart.id,
        "user_id": str(cart.user_id),
        "is_active": cart.is_active,
        "items": items,
        "total_items": totals["total_items"],
        "total_amount": totals["total_amount"],
        "created_at": cart.created_at.isoformat() if cart.created_at else None
    }


# ==================== ENDPOINTS ====================

@router.get("/")
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener el carrito del usuario autenticado.
    
    - Retorna el carrito con todos sus items
    - Incluye información completa de cada producto
    - Calcula totales automáticamente
    """
    cart = get_or_create_cart(str(current_user.id), db)
    cart_data = format_cart_response(cart)
    
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
    cart = get_or_create_cart(str(current_user.id), db)
    totals = calculate_cart_totals(cart)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Resumen del carrito",
        "data": totals
    }


@router.post("/items", status_code=201)
async def add_item_to_cart(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Agregar producto al carrito.
    
    - Si el producto ya existe, incrementa la cantidad
    - Valida que el producto exista y esté activo
    - Valida que haya stock suficiente
    """
    # Obtener o crear carrito
    cart = get_or_create_cart(str(current_user.id), db)
    
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
    
    # Verificar si el producto ya está en el carrito
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == item_data.product_id
    ).first()
    
    if existing_item:
        # Incrementar cantidad
        new_quantity = existing_item.quantity + item_data.quantity
        
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
        
        existing_item.quantity = new_quantity
        db.commit()
        db.refresh(existing_item)
        
        message = "Cantidad actualizada en el carrito"
    else:
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
        
        # Crear nuevo item
        new_item = CartItem(
            cart_id=cart.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        message = "Producto agregado al carrito"
    
    # Retornar carrito actualizado
    cart = db.query(Cart).filter(Cart.id == cart.id).first()
    cart_data = format_cart_response(cart)
    
    return {
        "success": True,
        "status_code": 201,
        "message": message,
        "data": cart_data
    }


@router.put("/items/{item_id}")
async def update_cart_item(
    item_id: int,
    item_data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar cantidad de un item del carrito.
    
    - Permite aumentar o disminuir la cantidad
    - Valida que el item pertenezca al usuario
    - Valida stock disponible
    """
    # Obtener carrito del usuario
    cart = get_or_create_cart(str(current_user.id), db)
    
    # Buscar el item
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Item no encontrado en el carrito",
                "error": "ITEM_NOT_FOUND"
            }
        )
    
    # Validar stock
    product = cart_item.product
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
    
    # Actualizar cantidad
    cart_item.quantity = item_data.quantity
    db.commit()
    db.refresh(cart_item)
    
    # Retornar carrito actualizado
    cart = db.query(Cart).filter(Cart.id == cart.id).first()
    cart_data = format_cart_response(cart)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Cantidad actualizada",
        "data": cart_data
    }


@router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar un item del carrito.
    """
    # Obtener carrito del usuario
    cart = get_or_create_cart(str(current_user.id), db)
    
    # Buscar el item
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Item no encontrado en el carrito",
                "error": "ITEM_NOT_FOUND"
            }
        )
    
    # Eliminar item
    db.delete(cart_item)
    db.commit()
    
    # Retornar carrito actualizado
    cart = db.query(Cart).filter(Cart.id == cart.id).first()
    cart_data = format_cart_response(cart)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Producto eliminado del carrito",
        "data": cart_data
    }


@router.delete("/clear")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Vaciar el carrito completamente.
    """
    # Obtener carrito del usuario
    cart = get_or_create_cart(str(current_user.id), db)
    
    # Eliminar todos los items
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    
    # Retornar carrito vacío
    cart = db.query(Cart).filter(Cart.id == cart.id).first()
    cart_data = format_cart_response(cart)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Carrito vaciado exitosamente",
        "data": cart_data
    }
