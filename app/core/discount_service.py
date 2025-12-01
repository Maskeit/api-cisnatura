"""
Utilidades para aplicar descuentos y ofertas a productos.
"""
from typing import Optional, Dict, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from models.admin_settings import AdminSettings
from models.products import Product


def get_active_settings(db: Session) -> Optional[AdminSettings]:
    """
    Obtener configuraciones administrativas.
    """
    return db.query(AdminSettings).first()


def is_seasonal_offer_active(offer: Dict, today: str = None) -> bool:
    """
    Verificar si una oferta temporal está activa hoy.
    
    Args:
        offer: Diccionario con start_date y end_date (formato YYYY-MM-DD)
        today: Fecha actual en formato YYYY-MM-DD (opcional)
    
    Returns:
        True si la oferta está activa
    """
    if not today:
        today = datetime.utcnow().strftime('%Y-%m-%d')
    
    start = offer.get('start_date', '')
    end = offer.get('end_date', '')
    
    if not start or not end:
        return False
    
    return start <= today <= end


def calculate_product_discount(
    product: Product,
    settings: AdminSettings
) -> Tuple[float, Optional[Dict]]:
    """
    Calcular el descuento aplicable a un producto.
    
    Prioridad de descuentos:
    1. Descuento específico del producto
    2. Oferta estacional activa para el producto
    3. Oferta estacional activa para la categoría del producto
    4. Descuento por categoría
    5. Descuento global
    
    Args:
        product: Objeto Product de SQLAlchemy
        settings: Objeto AdminSettings con las configuraciones
    
    Returns:
        Tupla (precio_final, info_descuento)
        - precio_final: Precio después de aplicar descuento
        - info_descuento: Dict con detalles del descuento o None
    """
    original_price = float(product.price)
    best_discount_percentage = 0.0
    discount_name = ""
    discount_source = ""
    
    if not settings:
        return original_price, None
    
    # 1. Descuento específico del producto
    if settings.product_discounts:
        product_discount = settings.product_discounts.get(str(product.id))
        if product_discount:
            best_discount_percentage = product_discount.get('percentage', 0)
            discount_name = product_discount.get('name', 'Oferta Especial')
            discount_source = "product"
    
    # 2. Ofertas estacionales para el producto
    if settings.seasonal_offers and best_discount_percentage == 0:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        for offer in settings.seasonal_offers:
            if not is_seasonal_offer_active(offer, today):
                continue
            
            # Verificar si aplica a este producto específico
            product_ids = offer.get('product_ids')
            if product_ids and str(product.id) in product_ids:
                offer_discount = offer.get('discount_percentage', 0)
                if offer_discount > best_discount_percentage:
                    best_discount_percentage = offer_discount
                    discount_name = offer.get('name', 'Oferta Temporal')
                    discount_source = "seasonal_product"
    
    # 3. Ofertas estacionales para la categoría
    if settings.seasonal_offers and best_discount_percentage == 0:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        for offer in settings.seasonal_offers:
            if not is_seasonal_offer_active(offer, today):
                continue
            
            # Verificar si aplica a la categoría del producto
            category_ids = offer.get('category_ids')
            
            # Si category_ids es None, aplica a todas las categorías
            if category_ids is None or str(product.category_id) in category_ids:
                offer_discount = offer.get('discount_percentage', 0)
                if offer_discount > best_discount_percentage:
                    best_discount_percentage = offer_discount
                    discount_name = offer.get('name', 'Oferta Temporal')
                    discount_source = "seasonal_category"
    
    # 4. Descuento por categoría
    if settings.category_discounts and best_discount_percentage == 0:
        category_discount = settings.category_discounts.get(str(product.category_id))
        if category_discount:
            best_discount_percentage = category_discount.get('percentage', 0)
            discount_name = category_discount.get('name', 'Oferta de Categoría')
            discount_source = "category"
    
    # 5. Descuento global
    if settings.global_discount_enabled and best_discount_percentage == 0:
        best_discount_percentage = settings.global_discount_percentage
        discount_name = settings.global_discount_name
        discount_source = "global"
    
    # Calcular precio final
    if best_discount_percentage > 0:
        discount_amount = original_price * (best_discount_percentage / 100)
        final_price = original_price - discount_amount
        
        discount_info = {
            "original_price": original_price,
            "discounted_price": round(final_price, 2),
            "discount_percentage": best_discount_percentage,
            "discount_name": discount_name,
            "discount_source": discount_source,
            "savings": round(discount_amount, 2),
            "is_active": True
        }
        
        return round(final_price, 2), discount_info
    
    return original_price, None


def apply_discounts_to_products(
    products: list,
    db: Session
) -> list:
    """
    Aplicar descuentos a una lista de productos.
    
    Args:
        products: Lista de objetos Product
        db: Sesión de base de datos
    
    Returns:
        Lista de diccionarios con productos y descuentos aplicados
    """
    settings = get_active_settings(db)
    result = []
    
    for product in products:
        final_price, discount_info = calculate_product_discount(product, settings)
        
        product_dict = {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "original_price": float(product.price),
            "price": final_price,  # Precio con descuento aplicado
            "stock": product.stock,
            "category_id": product.category_id,
            "image_url": product.image_url,
            "created_at": product.created_at.isoformat() if product.created_at else None
        }
        
        # Agregar info de descuento si existe
        if discount_info:
            product_dict["discount"] = discount_info
            product_dict["has_discount"] = True
        else:
            product_dict["has_discount"] = False
        
        result.append(product_dict)
    
    return result


def get_shipping_price(db: Session, order_total: float = 0.0) -> Dict:
    """
    Obtener precio de envío según configuraciones y total de la orden.
    
    Args:
        db: Sesión de base de datos
        order_total: Total de la orden
    
    Returns:
        Dict con shipping_price y is_free
    """
    settings = get_active_settings(db)
    
    if not settings:
        return {"shipping_price": 0.0, "is_free": False}
    
    # Verificar si califica para envío gratis
    if settings.free_shipping_threshold and order_total >= settings.free_shipping_threshold:
        return {
            "shipping_price": 0.0,
            "is_free": True,
            "threshold": settings.free_shipping_threshold,
            "message": f"¡Envío gratis por compra mayor a ${settings.free_shipping_threshold}!"
        }
    
    return {
        "shipping_price": settings.shipping_price,
        "is_free": False,
        "threshold": settings.free_shipping_threshold,
        "remaining_for_free": max(0, (settings.free_shipping_threshold or 0) - order_total) if settings.free_shipping_threshold else None
    }
