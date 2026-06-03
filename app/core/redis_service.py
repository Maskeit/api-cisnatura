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
    """Servicio para gestionar carritos en Redis.

    El carrito soporta items polimórficos: productos (físicos) y protocolos (digitales).
    Estructura normalizada de cada entrada:
        { "<item_type>:<id>": {"item_type": "product"|"protocol", "id": int, "quantity": int} }
    """

    CART_TTL = 7 * 24 * 60 * 60  # 7 días

    @staticmethod
    def _get_cart_key(user_id: str) -> str:
        """Generar clave de Redis para el carrito de un usuario"""
        return f"cart:{user_id}"

    @staticmethod
    def _entry_key(item_type: str, item_id: int) -> str:
        """Clave interna de un item dentro del carrito."""
        return f"{item_type}:{item_id}"

    @staticmethod
    def _normalize(cart: dict) -> dict:
        """Normaliza el carrito al formato polimórfico actual.

        Auto-migra entradas legacy (formato { "<product_id>": {"product_id", "quantity"} })
        que se guardaron antes de soportar protocolos, tratándolas como productos.
        """
        normalized = {}
        for key, value in cart.items():
            if isinstance(value, dict) and "item_type" in value and "id" in value:
                item_type = value["item_type"]
                item_id = int(value["id"])
            else:
                # Legacy: solo productos, la clave era el product_id numérico
                item_type = "product"
                item_id = int(value.get("product_id", key)) if isinstance(value, dict) else int(key)
            normalized[CartService._entry_key(item_type, item_id)] = {
                "item_type": item_type,
                "id": item_id,
                "quantity": value["quantity"],
            }
        return normalized

    @staticmethod
    def get_cart(user_id: str) -> dict:
        """Obtener carrito del usuario desde Redis (normalizado)."""
        cart_key = CartService._get_cart_key(user_id)
        cart_data = redis_client.get(cart_key)
        if not cart_data:
            return {}
        return CartService._normalize(json.loads(cart_data))

    @staticmethod
    def _save(user_id: str, cart: dict) -> None:
        cart_key = CartService._get_cart_key(user_id)
        if cart:
            redis_client.setex(cart_key, CartService.CART_TTL, json.dumps(cart))
        else:
            redis_client.delete(cart_key)

    @staticmethod
    def add_item(user_id: str, item_id: int, quantity: int = 1, item_type: str = "product") -> dict:
        """Agregar un item (producto o protocolo) al carrito en Redis."""
        cart = CartService.get_cart(user_id)
        key = CartService._entry_key(item_type, item_id)

        if key in cart:
            cart[key]["quantity"] += quantity
        else:
            cart[key] = {"item_type": item_type, "id": int(item_id), "quantity": quantity}

        CartService._save(user_id, cart)
        return cart

    @staticmethod
    def update_item_quantity(user_id: str, item_id: int, quantity: int, item_type: str = "product") -> dict:
        """Actualizar la cantidad de un item del carrito."""
        cart = CartService.get_cart(user_id)
        key = CartService._entry_key(item_type, item_id)

        if key in cart:
            if quantity <= 0:
                del cart[key]
            else:
                cart[key]["quantity"] = quantity

        CartService._save(user_id, cart)
        return cart

    @staticmethod
    def remove_item(user_id: str, item_id: int, item_type: str = "product") -> dict:
        """Eliminar un item del carrito."""
        return CartService.update_item_quantity(user_id, item_id, 0, item_type)

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


class TokenBlacklistService:
    """Servicio para gestionar tokens revocados (logout)"""
    
    @staticmethod
    def _get_blacklist_key(token_jti: str) -> str:
        """Generar clave de Redis para token revocado"""
        return f"blacklist:token:{token_jti}"
    
    @staticmethod
    def revoke_token(token_jti: str, expires_in_seconds: int) -> None:
        """Agregar token a la lista negra hasta que expire"""
        key = TokenBlacklistService._get_blacklist_key(token_jti)
        # El token se mantiene en la blacklist hasta su expiración natural
        redis_client.setex(key, expires_in_seconds, "revoked")
    
    @staticmethod
    def is_token_revoked(token_jti: str) -> bool:
        """Verificar si un token está revocado"""
        key = TokenBlacklistService._get_blacklist_key(token_jti)
        return redis_client.exists(key) > 0
