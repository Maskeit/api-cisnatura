"""
Payment Routes - Stripe Checkout Integration
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime
import logging
import json

from core.database import get_db
from core.dependencies import get_current_user
from core.payment_service import payment_service
from core.config import settings
from core.redis_service import CartService
from core.discount_service import calculate_product_discount, get_shipping_price
from models.user import User
from models.order import Order, OrderItem, OrderStatus, PaymentMethod
from models.addresses import Address
from models.products import Product
from models.admin_settings import AdminSettings

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)


@router.post("/stripe/create-checkout-session", response_model=Dict[str, Any])
async def create_stripe_checkout_session(
    checkout_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea sesión de Stripe Checkout desde el carrito.
    Requiere: address_id, payment_method (opcional), notes (opcional)
    """
    try:
        address_id = checkout_data.get("address_id")
        payment_method = checkout_data.get("payment_method", "stripe")
        notes = checkout_data.get("notes")
        
        if not address_id:
            raise HTTPException(status_code=400, detail="address_id es requerido")
        
        cart_service = CartService()
        cart_data = cart_service.get_cart(str(current_user.id))
        
        if not cart_data:
            raise HTTPException(status_code=400, detail="El carrito está vacío")
        
        address = db.query(Address).filter(
            Address.id == address_id,
            Address.user_id == current_user.id
        ).first()
        
        if not address:
            raise HTTPException(status_code=404, detail="Dirección no encontrada")
        
        items = []
        subtotal = Decimal("0.00")
        admin_settings = db.query(AdminSettings).first()
        
        for product_id_str, cart_item in cart_data.items():
            product_id = int(product_id_str)
            quantity = cart_item["quantity"]
            product = db.query(Product).filter(Product.id == product_id).first()
            
            if not product or not product.is_active:
                raise HTTPException(status_code=404, detail=f"Producto {product_id} no disponible")
            
            if product.stock < quantity:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente: {product.name}")
            
            if admin_settings:
                final_price, _ = calculate_product_discount(product, admin_settings)
            else:
                final_price = float(product.price)
            
            item_subtotal = Decimal(str(final_price)) * quantity
            subtotal += item_subtotal
            
            items.append({
                "title": product.name,
                "quantity": quantity,
                "unit_price": float(final_price),
                "currency_id": "MXN"
            })
        
        shipping_info = get_shipping_price(db, float(subtotal))
        shipping_cost = Decimal(str(shipping_info["shipping_price"]))
        
        if shipping_cost > 0:
            items.append({
                "title": "Envío",
                "quantity": 1,
                "unit_price": float(shipping_cost),
                "currency_id": "MXN"
            })
        elif shipping_info["is_free"]:
            items.append({
                "title": "Envío Gratis 🎉",
                "quantity": 1,
                "unit_price": 0.0,
                "currency_id": "MXN"
            })
        
        total = subtotal + shipping_cost
        
        result = payment_service.provider.create_payment(
            amount=total,
            currency="MXN",
            description=f"Compra - {current_user.email}",
            order_id=f"cart_{current_user.id}_{int(datetime.now().timestamp())}",
            customer_email=current_user.email,
            items=items,
            metadata={
                "success_url": f"{settings.FRONTEND_URL}/checkout/stripe/success?session_id={{CHECKOUT_SESSION_ID}}",
                "failure_url": f"{settings.FRONTEND_URL}/checkout/stripe/cancel",
                "user_id": str(current_user.id),
                "address_id": str(address_id),
                "payment_method": payment_method,
                "notes": notes or "",
                "subtotal": str(subtotal),
                "shipping_cost": str(shipping_cost),
                "total": str(total),
            }
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Checkout creado exitosamente",
                "data": {
                    "session_id": result["payment_id"],
                    "client_secret": result.get("client_secret"),
                    "url": result.get("checkout_url"),
                }
            }
        else:
            raise HTTPException(status_code=500, detail=f"Error al crear el pago: {result.get('error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Stripe checkout: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al procesar el pago")


@router.get("/stripe/session/{session_id}", response_model=Dict[str, Any])
async def get_stripe_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Obtiene información de una sesión de Stripe Checkout"""
    try:
        result = payment_service.provider.get_payment_status(session_id)
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "session_id": result["payment_id"],
                    "payment_intent": result.get("payment_intent_id"),
                    "payment_status": result["status"],
                    "amount_total": result.get("amount", 0),
                    "currency": result.get("currency", "mxn"),
                    "customer_email": result.get("customer_email"),
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"Error al consultar la sesión: {result.get('error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Stripe session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al consultar la sesión de pago")


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook de Stripe para eventos de pago.
    Eventos procesados:
    - checkout.session.completed
    - checkout.session.async_payment_succeeded
    - checkout.session.async_payment_failed
    - charge.refunded
    """
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")
        
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        if webhook_secret and signature:
            try:
                import stripe
                event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            except Exception as e:
                logger.error(f"Invalid Stripe webhook signature: {str(e)}")
                raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            event = json.loads(payload)
        
        event_type = event.get("type")
        event_data = event.get("data", {}).get("object", {})
        
        logger.info(f"Stripe webhook: {event_type}, ID: {event.get('id')}")
        
        if event_type == "checkout.session.completed":
            session_id = event_data.get("id")
            payment_status = event_data.get("payment_status")
            metadata = event_data.get("metadata", {})
            
            if payment_status == "paid":
                await _process_payment_success(db, session_id, event_data, metadata)
        
        elif event_type == "checkout.session.async_payment_succeeded":
            session_id = event_data.get("id")
            metadata = event_data.get("metadata", {})
            await _process_payment_success(db, session_id, event_data, metadata)
        
        elif event_type == "checkout.session.async_payment_failed":
            session_id = event_data.get("id")
            metadata = event_data.get("metadata", {})
            await _handle_payment_failure(db, session_id, metadata)
        
        elif event_type == "charge.refunded":
            payment_intent_id = event_data.get("payment_intent")
            refund_amount = event_data.get("amount_refunded", 0) / 100
            await _handle_refund(db, payment_intent_id, refund_amount)
        
        return {"success": True, "message": "Webhook received"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}", exc_info=True)
        return {"success": True, "message": "Webhook received (error logged)"}


async def _process_payment_success(
    db: Session,
    session_id: str,
    session_data: dict,
    metadata: dict
):
    """Procesa pago exitoso y crea orden"""
    user_id = metadata.get("user_id")
    address_id = int(metadata.get("address_id", 0))
    payment_method = metadata.get("payment_method", "stripe")
    notes = metadata.get("notes")
    subtotal = Decimal(metadata.get("subtotal", "0"))
    shipping_cost = Decimal(metadata.get("shipping_cost", "0"))
    total = Decimal(metadata.get("total", "0"))
    
    if not user_id or not address_id:
        logger.error(f"Missing user_id or address_id for session {session_id}")
        return
    
    existing_order = db.query(Order).filter(Order.payment_id == session_id).first()
    if existing_order:
        logger.info(f"Order already exists for session {session_id}")
        return
    
    cart_service = CartService()
    cart_data = cart_service.get_cart(user_id)
    
    if not cart_data:
        logger.error(f"Cart empty for user {user_id}")
        return
    
    new_order = Order(
        user_id=user_id,
        address_id=address_id,
        payment_method=PaymentMethod(payment_method),
        payment_id=session_id,
        payment_status="paid",
        status=OrderStatus.PAID,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=Decimal("0.00"),
        total=total,
        notes=notes,
        paid_at=datetime.now()
    )
    
    db.add(new_order)
    db.flush()
    
    for product_id_str, cart_item in cart_data.items():
        product_id = int(product_id_str)
        quantity = cart_item["quantity"]
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if product:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=quantity,
                unit_price=Decimal(str(product.price)),
                subtotal=Decimal(str(product.price)) * quantity
            )
            db.add(order_item)
            product.stock -= quantity
    
    db.commit()
    cart_service.clear_cart(user_id)
    
    logger.info(f"Order {new_order.id} created from session {session_id}")


async def _handle_payment_failure(db: Session, session_id: str, metadata: dict):
    """Maneja pago fallido"""
    order = db.query(Order).filter(Order.payment_id == session_id).first()
    
    if order:
        order.status = OrderStatus.CANCELLED
        order.payment_status = "failed"
        
        for item in order.order_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
        
        db.commit()
        logger.info(f"Order {order.id} cancelled due to payment failure")


async def _handle_refund(db: Session, payment_intent_id: str, refund_amount: float):
    """Maneja reembolso"""
    orders = db.query(Order).filter(
        Order.payment_method == PaymentMethod.STRIPE,
        Order.payment_status == "paid"
    ).order_by(desc(Order.paid_at)).limit(50).all()
    
    for order in orders:
        try:
            result = payment_service.provider.get_payment_status(order.payment_id)
            if result.get("payment_intent_id") == payment_intent_id:
                order.status = OrderStatus.REFUNDED
                order.payment_status = "refunded"
                
                for item in order.order_items:
                    product = db.query(Product).filter(Product.id == item.product_id).first()
                    if product:
                        product.stock += item.quantity
                
                db.commit()
                logger.info(f"Order {order.id} refunded, stock restored")
                return
        except Exception:
            continue
    
    logger.warning(f"No order found for refunded payment_intent: {payment_intent_id}")


@router.post("/cancel/{payment_id}")
async def cancel_payment(payment_id: str, current_user: User = Depends(get_current_user)):
    """Cancela un pago (solo admin)"""
    if not current_user.is_admin:
        raise HTTPException(403, "No autorizado")
    
    try:
        result = payment_service.provider.cancel_payment(payment_id)
        
        if result["success"]:
            return {"success": True, "message": "Pago cancelado exitosamente"}
        else:
            raise HTTPException(400, detail=f"Error: {result.get('error')}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling payment: {str(e)}")
        raise HTTPException(500, "Error al cancelar el pago")


@router.post("/refund/{payment_id}")
async def refund_payment(
    payment_id: str,
    amount: float = None,
    current_user: User = Depends(get_current_user)
):
    """Realiza reembolso total o parcial (solo admin)"""
    if not current_user.is_admin:
        raise HTTPException(403, "No autorizado")
    
    try:
        refund_amount = Decimal(str(amount)) if amount else None
        result = payment_service.provider.refund_payment(payment_id, amount=refund_amount)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Reembolso procesado exitosamente",
                "data": {
                    "refund_id": result.get("refund_id"),
                    "amount": result.get("amount")
                }
            }
        else:
            raise HTTPException(400, detail=f"Error: {result.get('error')}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing refund: {str(e)}")
        raise HTTPException(500, "Error al procesar el reembolso")
