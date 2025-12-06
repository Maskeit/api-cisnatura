"""
Stripe Payment Provider Implementation
Implementa la interfaz PaymentProvider para Stripe.
"""

import stripe
from typing import Dict, Any, Optional
from decimal import Decimal
import logging

from core.payment_service import PaymentProvider

logger = logging.getLogger(__name__)


class StripeProvider(PaymentProvider):
    """
    Implementación del proveedor de pagos Stripe.
    Usa Stripe Checkout para manejar el flujo de pago.
    """
    
    def __init__(self, api_key: str, webhook_secret: str):
        """
        Args:
            api_key: Secret Key de Stripe (test o producción)
            webhook_secret: Webhook signing secret para validar webhooks
        """
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.stripe = stripe
    
    def initialize(self) -> None:
        """
        Inicializa el SDK de Stripe con las credenciales.
        """
        try:
            self.stripe.api_key = self.api_key
            logger.info("Stripe SDK initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Stripe SDK: {str(e)}")
            raise
    
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
        Crea una sesión de Stripe Checkout.
        
        Stripe usa "checkout sessions" para crear el flujo de pago.
        """
        try:
            # Convertir items al formato de Stripe line_items
            line_items = []
            
            if items and len(items) > 0:
                for item in items:
                    line_items.append({
                        "price_data": {
                            "currency": currency.lower(),
                            "unit_amount": int(item["unit_price"] * 100),  # Centavos
                            "product_data": {
                                "name": item["title"],
                            },
                        },
                        "quantity": item["quantity"],
                    })
            else:
                # Item genérico si no se proporcionan items
                line_items.append({
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": int(amount * 100),  # Centavos
                        "product_data": {
                            "name": description,
                        },
                    },
                    "quantity": 1,
                })
            
            # Preparar metadata adicional
            session_metadata = {
                "order_id": order_id,
                "external_reference": order_id,
            }
            
            if metadata:
                # Agregar metadata personalizada
                for key, value in metadata.items():
                    if key not in ["success_url", "failure_url", "pending_url"]:
                        session_metadata[key] = str(value)
            
            # URLs de retorno
            success_url = metadata.get("success_url") if metadata else None
            cancel_url = metadata.get("failure_url") if metadata else None
            
            # Crear sesión de checkout
            checkout_session = self.stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=success_url or "https://example.com/success",
                cancel_url=cancel_url or "https://example.com/cancel",
                customer_email=customer_email,
                metadata=session_metadata,
                payment_intent_data={
                    "metadata": session_metadata,
                },
            )
            
            logger.info(
                f"Stripe checkout session created: {checkout_session.id} "
                f"for order: {order_id}"
            )
            
            # Retornar respuesta en formato estándar
            return {
                "success": True,
                "payment_id": checkout_session.id,
                "status": "pending",
                "checkout_url": checkout_session.url,
                "client_secret": getattr(checkout_session, "client_secret", None),
                "raw_response": checkout_session
            }
            
        except Exception as e:
            logger.error(f"Error creating Stripe payment: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de un pago en Stripe.
        
        Args:
            payment_id: ID de la sesión de checkout o payment_intent
        """
        try:
            # Determinar si es una sesión de checkout o un payment_intent
            if payment_id.startswith("cs_"):
                # Es una sesión de checkout
                session = self.stripe.checkout.Session.retrieve(
                    payment_id,
                    expand=["payment_intent"]
                )
                
                payment_intent = session.payment_intent
                
                return {
                    "success": True,
                    "payment_id": session.id,
                    "status": self._map_stripe_status(session.payment_status),
                    "status_detail": session.payment_status,
                    "amount": session.amount_total / 100 if session.amount_total else 0,
                    "currency": session.currency,
                    "customer_email": session.customer_email,
                    "external_reference": session.metadata.get("order_id"),
                    "metadata": dict(session.metadata),
                    "payment_intent_id": payment_intent.id if payment_intent else None,
                    "raw_response": session
                }
            
            elif payment_id.startswith("pi_"):
                # Es un payment_intent
                payment_intent = self.stripe.PaymentIntent.retrieve(payment_id)
                
                return {
                    "success": True,
                    "payment_id": payment_intent.id,
                    "status": self._map_stripe_status(payment_intent.status),
                    "status_detail": payment_intent.status,
                    "amount": payment_intent.amount / 100 if payment_intent.amount else 0,
                    "currency": payment_intent.currency,
                    "external_reference": payment_intent.metadata.get("order_id"),
                    "metadata": dict(payment_intent.metadata),
                    "raw_response": payment_intent
                }
            
            else:
                return {
                    "success": False,
                    "error": "Invalid payment ID format"
                }
                
        except Exception as e:
            logger.error(f"Error getting Stripe payment status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Cancela un payment intent pendiente.
        
        Args:
            payment_id: ID del payment_intent
        """
        try:
            if payment_id.startswith("pi_"):
                payment_intent = self.stripe.PaymentIntent.cancel(payment_id)
                
                return {
                    "success": True,
                    "payment_id": payment_intent.id,
                    "status": payment_intent.status,
                    "message": "Payment cancelled"
                }
            else:
                return {
                    "success": False,
                    "error": "Can only cancel payment intents"
                }
                
        except Exception as e:
            logger.error(f"Error cancelling Stripe payment: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Realiza un reembolso total o parcial.
        
        Args:
            payment_id: ID del payment_intent
            amount: Monto a reembolsar en la moneda original (None = reembolso total)
        """
        try:
            refund_data = {"payment_intent": payment_id}
            
            if amount:
                # Reembolso parcial (convertir a centavos)
                refund_data["amount"] = int(amount * 100)
            
            refund = self.stripe.Refund.create(**refund_data)
            
            logger.info(f"Stripe refund created: {refund.id} for payment {payment_id}")
            
            return {
                "success": True,
                "refund_id": refund.id,
                "payment_id": payment_id,
                "amount": refund.amount / 100 if refund.amount else 0,
                "status": refund.status,
                "raw_response": refund
            }
            
        except Exception as e:
            logger.error(f"Error creating Stripe refund: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Valida la firma de un webhook de Stripe.
        
        Args:
            payload: Cuerpo de la petición (bytes)
            signature: Firma del header Stripe-Signature
            secret: Webhook signing secret
            
        Returns:
            True si la firma es válida
        """
        try:
            self.stripe.Webhook.construct_event(
                payload, signature, secret
            )
            return True
        except Exception as e:
            logger.error(f"Stripe webhook validation failed: {str(e)}")
            return False
    
    def _map_stripe_status(self, stripe_status: str) -> str:
        """
        Mapea estados de Stripe a estados internos compatibles con.
        
        Stripe Status -> Internal Status
        - paid -> approved
        - unpaid -> pending
        - no_payment_required -> approved
        - succeeded -> approved
        - processing -> pending
        - requires_action -> pending
        - requires_payment_method -> pending
        - canceled -> cancelled
        - failed -> rejected
        """
        status_map = {
            "paid": "approved",
            "unpaid": "pending",
            "no_payment_required": "approved",
            "succeeded": "approved",
            "processing": "pending",
            "requires_action": "pending",
            "requires_payment_method": "pending",
            "requires_confirmation": "pending",
            "requires_capture": "authorized",
            "canceled": "cancelled",
            "cancelled": "cancelled",
            "failed": "rejected",
        }
        
        return status_map.get(stripe_status, stripe_status)
