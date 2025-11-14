"""
Servicio para gestionar carritos en Redis.
Redis se usa para carritos temporales (volátiles, rápidos).
PostgreSQL se usa solo cuando se confirma la compra.
"""
import json
import redis
from typing import List, Optional
from core.config import settings

# Conexión a Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class CartService:
    """Servicio para gestionar carritos en Redis"""
    
    @staticmethod
    def _get_cart_key(user_id: str) -> str:
        """Generar clave de Redis para el carrito de un usuario"""
        return f"cart:{user_id}"
    
    @staticmethod
    def add_item(user_id: str, product_id: int, quantity: int = 1) -> dict:
        """Agregar producto al carrito en Redis"""
        cart_key = CartService._get_cart_key(user_id)
        
        # Obtener carrito actual
        cart_data = redis_client.get(cart_key)
        cart = json.loads(cart_data) if cart_data else {}
        
        # Agregar o actualizar producto
        product_id_str = str(product_id)
        if product_id_str in cart:
            cart[product_id_str]["quantity"] += quantity
        else:
            cart[product_id_str] = {
                "product_id": product_id,
                "quantity": quantity
            }
        
        # Guardar en Redis con expiración de 7 días
        redis_client.setex(cart_key, 7 * 24 * 60 * 60, json.dumps(cart))
        
        return cart
    
    @staticmethod
    def get_cart(user_id: str) -> dict:
        """Obtener carrito del usuario desde Redis"""
        cart_key = CartService._get_cart_key(user_id)
        cart_data = redis_client.get(cart_key)
        return json.loads(cart_data) if cart_data else {}
    
    @staticmethod
    def update_item_quantity(user_id: str, product_id: int, quantity: int) -> dict:
        """Actualizar cantidad de un producto en el carrito"""
        cart_key = CartService._get_cart_key(user_id)
        cart_data = redis_client.get(cart_key)
        
        if not cart_data:
            return {}
        
        cart = json.loads(cart_data)
        product_id_str = str(product_id)
        
        if product_id_str in cart:
            if quantity <= 0:
                del cart[product_id_str]
            else:
                cart[product_id_str]["quantity"] = quantity
        
        if cart:
            redis_client.setex(cart_key, 7 * 24 * 60 * 60, json.dumps(cart))
        else:
            redis_client.delete(cart_key)
        
        return cart
    
    @staticmethod
    def remove_item(user_id: str, product_id: int) -> dict:
        """Eliminar producto del carrito"""
        return CartService.update_item_quantity(user_id, product_id, 0)
    
    @staticmethod
    def clear_cart(user_id: str) -> None:
        """Limpiar carrito del usuario"""
        cart_key = CartService._get_cart_key(user_id)
        redis_client.delete(cart_key)
    
    @staticmethod
    def get_cart_count(user_id: str) -> int:
        """Obtener cantidad total de items en el carrito"""
        cart = CartService.get_cart(user_id)
        return sum(item["quantity"] for item in cart.values())


class CacheService:
    """Servicio para cachear datos frecuentes en Redis"""
    
    @staticmethod
    def cache_products(key: str, products: list, expire_seconds: int = 300) -> None:
        """Cachear listado de productos (5 minutos por defecto)"""
        redis_client.setex(key, expire_seconds, json.dumps(products))
    
    @staticmethod
    def get_cached_products(key: str) -> Optional[list]:
        """Obtener productos cacheados"""
        data = redis_client.get(key)
        return json.loads(data) if data else None
    
    @staticmethod
    def invalidate_cache(pattern: str) -> None:
        """Invalidar cache por patrón"""
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
