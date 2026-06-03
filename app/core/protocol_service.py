"""
EJEMPLO: Servicio para gestionar acceso a protocolos después de compra
Este archivo muestra cómo integrar el acceso automático a protocolos.

IMPLEMENTACIÓN:
1. Cuando una orden se marca como PAID o DELIVERED
2. Se ejecuta este servicio para crear ProtocolAccess
3. El usuario puede ver el protocolo en su cuenta
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from models.protocols import Protocol, ProtocolAccess, ProtocolProgress
from models.order import Order, OrderItem, OrderStatus
from models.products import Product


class ProtocolAccessService:
    """Servicio para gestionar acceso a protocolos"""
    
    @staticmethod
    def grant_protocol_access(
        order: Order,
        db: Session,
        access_duration_days: Optional[int] = None
    ) -> list:
        """
        Otorgar acceso a todos los protocolos en una orden completada.
        
        Se ejecuta cuando una orden se marca como PAID o DELIVERED.
        
        Args:
            order: Orden completada
            db: Sesión de BD
            access_duration_days: Duración del acceso en días (None = indefinido)
        
        Returns:
            Lista de ProtocolAccess creados
        """
        created_accesses = []
        
        # Iterar sobre los items de la orden
        for order_item in order.order_items:
            # Verificar si el producto es un protocolo
            protocol = db.query(Protocol).filter(
                Protocol.product_id == order_item.product_id
            ).first()
            
            if not protocol:
                # No es un protocolo, ignorar
                continue
            
            # Verificar que el usuario no tenga acceso ya
            existing_access = db.query(ProtocolAccess).filter(
                ProtocolAccess.protocol_id == protocol.id,
                ProtocolAccess.user_id == order.user_id,
                ProtocolAccess.is_active == True
            ).first()
            
            if existing_access:
                print(f"Usuario {order.user_id} ya tiene acceso al protocolo {protocol.id}")
                continue
            
            # Crear acceso
            access_until = None
            if access_duration_days:
                access_until = datetime.utcnow() + timedelta(days=access_duration_days)
            
            protocol_access = ProtocolAccess(
                protocol_id=protocol.id,
                user_id=order.user_id,
                order_id=order.id,
                order_item_id=order_item.id,
                is_active=True,
                access_until=access_until,
                granted_at=datetime.utcnow()
            )
            
            db.add(protocol_access)
            created_accesses.append(protocol_access)
            
            print(f"✓ Acceso otorgado: Usuario {order.user_id} → Protocolo {protocol.id}")
        
        db.commit()
        return created_accesses
    
    @staticmethod
    def revoke_protocol_access(
        protocol_access: ProtocolAccess,
        db: Session
    ) -> None:
        """
        Revocar acceso a un protocolo.
        Desactiva el acceso sin eliminar el registro.
        """
        protocol_access.is_active = False
        protocol_access.revoked_at = datetime.utcnow()
        db.commit()
    
    @staticmethod
    def initialize_protocol_progress(
        user_id,
        protocol: Protocol,
        db: Session
    ) -> 'ProtocolProgress':
        """
        Inicializar el seguimiento de progreso para un usuario en un protocolo.
        Se ejecuta cuando el usuario accede por primera vez.
        """
        from models.protocols import ProtocolProgress
        
        # Verificar que no existe ya
        existing_progress = db.query(ProtocolProgress).filter(
            ProtocolProgress.protocol_id == protocol.id,
            ProtocolProgress.user_id == user_id
        ).first()
        
        if existing_progress:
            return existing_progress
        
        # Crear progress
        progress = ProtocolProgress(
            protocol_id=protocol.id,
            user_id=user_id,
            total_phases=len(protocol.phases),
            current_phase_order=0,
            completed_phases=0,
            started_at=datetime.utcnow()
        )
        
        db.add(progress)
        db.commit()
        db.refresh(progress)
        
        return progress
    
    @staticmethod
    def check_expired_access(db: Session) -> int:
        """
        Revocar acceso expirado a protocolos.
        Debe ejecutarse periódicamente (cron job).
        
        Returns:
            Número de accesos revocados
        """
        from datetime import datetime
        
        # Encontrar accesos expirados
        expired_accesses = db.query(ProtocolAccess).filter(
            ProtocolAccess.is_active == True,
            ProtocolAccess.access_until < datetime.utcnow()
        ).all()
        
        count = 0
        for access in expired_accesses:
            access.is_active = False
            access.revoked_at = datetime.utcnow()
            count += 1
        
        db.commit()
        print(f"✓ {count} accesos a protocolos revocados por expiración")
        
        return count


# ==================== EJEMPLO DE INTEGRACIÓN ====================
"""
DÓNDE IMPLEMENTAR:

1. En el endpoint de completar orden (cuando status cambia a PAID o DELIVERED):

    @router.post("/orders/{order_id}/complete")
    async def complete_order(order_id: int, db: Session = Depends(get_db)):
        order = db.query(Order).filter(Order.id == order_id).first()
        order.status = OrderStatus.DELIVERED  # o PAID
        db.commit()
        
        # Otorgar acceso a protocolos
        ProtocolAccessService.grant_protocol_access(order, db)
        
        return {"success": True}

2. En un webhook de pago (Stripe, etc.):

    @router.post("/webhooks/stripe")
    async def stripe_webhook(payload: dict, db: Session = Depends(get_db)):
        if payload['type'] == 'payment_intent.succeeded':
            order_id = payload['data']['order_id']
            order = db.query(Order).filter(Order.id == order_id).first()
            order.status = OrderStatus.PAID
            db.commit()
            
            # Otorgar acceso automáticamente
            ProtocolAccessService.grant_protocol_access(order, db)

3. En un celery task (limpieza periódica):

    @celery_app.task
    def cleanup_expired_protocol_access():
        db = SessionLocal()
        try:
            ProtocolAccessService.check_expired_access(db)
        finally:
            db.close()
    
    # En schedules:
    app.conf.beat_schedule = {
        'check-expired-protocol-access': {
            'task': 'core.tasks.cleanup_expired_protocol_access',
            'schedule': crontab(hour=0, minute=0),  # Diariamente a medianoche
        },
    }
"""
