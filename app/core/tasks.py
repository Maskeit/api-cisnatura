"""
Tareas automáticas y programadas del sistema.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from core.database import SessionLocal
from models.user import User
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def delete_unverified_users():
    """
    Eliminar usuarios no verificados después de 24 horas.
    Se ejecuta automáticamente cada hora.
    
    Solo elimina usuarios que:
    - No han verificado su email (email_verified = False)
    - No son administradores (is_admin = False)
    - Fueron creados hace más de 24 horas
    """
    db = SessionLocal()
    try:
        # Calcular el tiempo límite (24 horas atrás)
        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Buscar usuarios a eliminar
        unverified_users = db.query(User).filter(
            User.email_verified == False,
            User.is_admin == False,
            User.created_at < time_limit
        ).all()
        
        if unverified_users:
            count = len(unverified_users)
            emails = [u.email for u in unverified_users]
            
            # Eliminar usuarios
            for user in unverified_users:
                db.delete(user)
            
            db.commit()
            
            logger.info(
                f"✅ Tarea automática: {count} usuario(s) no verificado(s) eliminado(s). "
                f"Emails: {', '.join(emails)}"
            )
        else:
            logger.debug("✅ Tarea automática: No hay usuarios no verificados para eliminar.")
            
    except Exception as e:
        logger.error(f"❌ Error al eliminar usuarios no verificados: {str(e)}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """
    Iniciar el scheduler de tareas automáticas.
    Se llama al startup de la aplicación.
    """
    if not scheduler.running:
        # Agregar trabajo: ejecutar cada hora
        scheduler.add_job(
            delete_unverified_users,
            'interval',
            hours=8,
            id='delete_unverified_users',
            name='Eliminar usuarios no verificados cada 24+ horas',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Scheduler de tareas automáticas iniciado")


def stop_scheduler():
    """
    Detener el scheduler de tareas automáticas.
    Se llama al shutdown de la aplicación.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✅ Scheduler de tareas automáticas detenido")
