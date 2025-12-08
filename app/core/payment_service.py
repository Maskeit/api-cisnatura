"""
Payment Service - Abstract Payment Provider Interface
Permite integrar múltiples pasarelas de pago con una interfaz común.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal


class PaymentProvider(ABC):
    """
    Interfaz abstracta para proveedores de pago.
    Cada proveedor ( Stripe, etc.) debe implementar estos métodos.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Inicializa el SDK del proveedor de pago.
        """
        pass
    
    @abstractmethod
    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        order_id: str,
        customer_email: str,
        items: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crea una intención de pago.
        
        Args:
            amount: Monto a cobrar
            currency: Código de moneda (USD, MXN, etc.)
            description: Descripción del pago
            order_id: ID de la orden en el sistema
            customer_email: Email del cliente
            items: Lista de items detallados (título, cantidad, precio)
            metadata: Datos adicionales
            
        Returns:
            Dict con la respuesta del proveedor, debe incluir:
            - payment_id: ID del pago en el proveedor
            - status: Estado del pago
            - checkout_url: URL para redirigir al cliente (opcional)
            - otros campos específicos del proveedor
        """
        pass
    
    @abstractmethod
    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado actual de un pago.
        
        Args:
            payment_id: ID del pago en el proveedor
            
        Returns:
            Dict con el estado del pago
        """
        pass
    
    @abstractmethod
    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Cancela un pago pendiente.
        
        Args:
            payment_id: ID del pago en el proveedor
            
        Returns:
            Dict con la confirmación de cancelación
        """
        pass
    
    @abstractmethod
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Realiza un reembolso total o parcial.
        
        Args:
            payment_id: ID del pago en el proveedor
            amount: Monto a reembolsar (None = reembolso total)
            
        Returns:
            Dict con la confirmación del reembolso
        """
        pass
    
    @abstractmethod
    def validate_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Valida la firma de un webhook del proveedor.
        
        Args:
            payload: Cuerpo de la petición
            signature: Firma enviada por el proveedor
            secret: Secret para validar la firma
            
        Returns:
            True si la firma es válida
        """
        pass


class PaymentService:
    """
    Servicio de pagos que gestiona el proveedor activo.
    Patrón Factory para seleccionar el proveedor según configuración.
    """
    
    def __init__(self):
        self._provider: Optional[PaymentProvider] = None
    
    def initialize(self, provider_name: str, **config) -> None:
        """
        Inicializa el proveedor de pago según el nombre.
        
        Args:
            provider_name: Nombre del proveedor (stripe, etc.)
            **config: Configuración específica del proveedor
        """
        if provider_name == "stripe":
            from core.payment_providers.stripe import StripeProvider
            self._provider = StripeProvider(**config)
        else:
            raise ValueError(f"Proveedor de pago no soportado: {provider_name}")
        
        self._provider.initialize()
    
    @property
    def provider(self) -> PaymentProvider:
        """
        Obtiene el proveedor de pago activo.
        """
        if not self._provider:
            raise RuntimeError("Payment service not initialized")
        return self._provider


# Instancia global del servicio de pagos
payment_service = PaymentService()
