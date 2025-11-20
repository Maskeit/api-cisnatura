from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from core.database import get_db
from core.dependencies import get_current_user, get_current_admin_user
from core.security import verify_password, hash_password
from models.user import User
from models.order import Order, OrderStatus
from models.addresses import Address
from schemas.users import (
    UserProfileResponse,
    UserUpdateProfile,
    UserChangePassword,
    UserProfileSummary,
    UserAdminResponse,
    UserAdminUpdate,
    UserAdminFilters,
    UserAdminStats,
    UserBanRequest
)

router = APIRouter(
    prefix="/users",
    tags=["users"]
)


# ==================== USER PROFILE ENDPOINTS ====================

@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener perfil del usuario actual.
    
    Retorna la información básica del perfil del usuario autenticado.
    """
    return {
        "success": True,
        "status_code": 200,
        "message": "Perfil obtenido exitosamente",
        "data": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "is_admin": current_user.is_admin,
            "email_verified": current_user.email_verified,
            "email_verified_at": current_user.email_verified_at,
            "created_at": current_user.created_at
        }
    }


@router.get("/me/summary")
async def get_my_profile_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener resumen completo del perfil con estadísticas.
    
    Incluye:
    - Información del perfil
    - Total de órdenes (completadas, pendientes)
    - Total gastado
    - Direcciones guardadas
    - Última orden
    """
    # Estadísticas de órdenes
    total_orders = db.query(Order).filter(Order.user_id == current_user.id).count()
    
    completed_orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.status == OrderStatus.DELIVERED
    ).count()
    
    pending_orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.status.in_([
            OrderStatus.PENDING,
            OrderStatus.PAYMENT_PENDING,
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED
        ])
    ).count()
    
    # Total gastado (solo órdenes completadas)
    total_spent = db.query(func.sum(Order.total)).filter(
        Order.user_id == current_user.id,
        Order.status == OrderStatus.DELIVERED
    ).scalar() or Decimal('0')
    
    # Direcciones
    total_addresses = db.query(Address).filter(Address.user_id == current_user.id).count()
    has_default_address = db.query(Address).filter(
        Address.user_id == current_user.id,
        Address.is_default == True
    ).first() is not None
    
    # Última orden
    last_order = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(desc(Order.created_at)).first()
    
    last_order_data = None
    if last_order:
        last_order_data = {
            "id": last_order.id,
            "status": last_order.status,
            "total": float(last_order.total),
            "created_at": last_order.created_at.isoformat()
        }
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Resumen de perfil obtenido exitosamente",
        "data": {
            "profile": {
                "id": str(current_user.id),
                "email": current_user.email,
                "full_name": current_user.full_name,
                "is_active": current_user.is_active,
                "is_admin": current_user.is_admin,
                "email_verified": current_user.email_verified,
                "email_verified_at": current_user.email_verified_at,
                "created_at": current_user.created_at
            },
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "pending_orders": pending_orders,
            "total_spent": float(total_spent),
            "total_addresses": total_addresses,
            "has_default_address": has_default_address,
            "last_order": last_order_data
        }
    }


@router.put("/me")
async def update_my_profile(
    profile_data: UserUpdateProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar perfil del usuario actual.
    
    Permite actualizar:
    - Nombre completo
    """
    # Actualizar solo campos enviados
    if profile_data.full_name:
        current_user.full_name = profile_data.full_name
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Perfil actualizado exitosamente",
        "data": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "is_admin": current_user.is_admin,
            "email_verified": current_user.email_verified,
            "email_verified_at": current_user.email_verified_at,
            "created_at": current_user.created_at
        }
    }


@router.post("/me/change-password")
async def change_my_password(
    password_data: UserChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cambiar contraseña del usuario actual.
    
    Requiere:
    - Contraseña actual (para verificación)
    - Nueva contraseña (mínimo 8 caracteres)
    - Confirmación de nueva contraseña
    """
    # Verificar contraseña actual
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "Contraseña actual incorrecta",
                "error": "INVALID_PASSWORD"
            }
        )
    
    # Actualizar contraseña
    current_user.hashed_password = hash_password(password_data.new_password)
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Contraseña actualizada exitosamente"
    }


@router.delete("/me")
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar cuenta del usuario actual (soft delete).
    
    Desactiva la cuenta en lugar de eliminarla permanentemente.
    El usuario no podrá iniciar sesión hasta que un admin la reactive.
    """
    # Verificar que no tenga órdenes pendientes
    pending_orders = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.status.in_([
            OrderStatus.PENDING,
            OrderStatus.PAYMENT_PENDING,
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED
        ])
    ).count()
    
    if pending_orders > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"No puedes eliminar tu cuenta con {pending_orders} órdenes pendientes",
                "error": "PENDING_ORDERS"
            }
        )
    
    # Soft delete: solo desactivar
    current_user.is_active = False
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Cuenta desactivada exitosamente"
    }


# ==================== ADMIN USER MANAGEMENT ENDPOINTS ====================

@router.get("/admin/users")
async def list_users_admin(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(20, ge=1, le=100, description="Usuarios por página"),
    search: Optional[str] = Query(None, description="Buscar por email o nombre"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    is_admin: Optional[bool] = Query(None, description="Filtrar por rol admin"),
    email_verified: Optional[bool] = Query(None, description="Filtrar por email verificado"),
    created_from: Optional[datetime] = Query(None, description="Registros desde"),
    created_to: Optional[datetime] = Query(None, description="Registros hasta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Listar todos los usuarios (solo admin).
    
    Permite filtrar por:
    - Estado (activo/inactivo)
    - Rol (admin/usuario)
    - Email verificado
    - Búsqueda por email o nombre
    - Rango de fechas de registro
    """
    # Query base
    query = db.query(User)
    
    # Aplicar filtros
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_pattern)) |
            (User.full_name.ilike(search_pattern))
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)
    
    if email_verified is not None:
        query = query.filter(User.email_verified == email_verified)
    
    if created_from:
        query = query.filter(User.created_at >= created_from)
    
    if created_to:
        query = query.filter(User.created_at <= created_to)
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación
    offset = (page - 1) * limit
    users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()
    
    # Agregar estadísticas a cada usuario
    users_data = []
    for user in users:
        total_orders = db.query(Order).filter(Order.user_id == user.id).count()
        total_spent = db.query(func.sum(Order.total)).filter(
            Order.user_id == user.id,
            Order.status == OrderStatus.DELIVERED
        ).scalar() or Decimal('0')
        total_addresses = db.query(Address).filter(Address.user_id == user.id).count()
        
        user_dict = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "email_verified": user.email_verified,
            "email_verified_at": user.email_verified_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "total_orders": total_orders,
            "total_spent": float(total_spent),
            "total_addresses": total_addresses
        }
        users_data.append(user_dict)
    
    # Calcular metadata de paginación
    total_pages = (total + limit - 1) // limit
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Usuarios obtenidos exitosamente",
        "data": {
            "users": users_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    }


@router.get("/admin/users/{user_id}")
async def get_user_admin(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener detalles completos de un usuario (solo admin).
    
    Incluye:
    - Información del perfil
    - Estadísticas de órdenes
    - Direcciones guardadas
    - Última actividad
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Usuario no encontrado",
                "error": "USER_NOT_FOUND"
            }
        )
    
    # Estadísticas
    total_orders = db.query(Order).filter(Order.user_id == user.id).count()
    total_spent = db.query(func.sum(Order.total)).filter(
        Order.user_id == user.id,
        Order.status == OrderStatus.DELIVERED
    ).scalar() or Decimal('0')
    total_addresses = db.query(Address).filter(Address.user_id == user.id).count()
    
    # Últimas órdenes
    recent_orders = db.query(Order).filter(
        Order.user_id == user.id
    ).order_by(desc(Order.created_at)).limit(5).all()
    
    orders_data = [
        {
            "id": order.id,
            "status": order.status,
            "total": float(order.total),
            "created_at": order.created_at.isoformat()
        }
        for order in recent_orders
    ]
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Usuario obtenido exitosamente",
        "data": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "email_verified": user.email_verified,
            "email_verified_at": user.email_verified_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "total_orders": total_orders,
            "total_spent": float(total_spent),
            "total_addresses": total_addresses,
            "recent_orders": orders_data
        }
    }


@router.patch("/admin/users/{user_id}")
async def update_user_admin(
    user_id: str,
    user_data: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar usuario (solo admin).
    
    Permite modificar:
    - Nombre completo
    - Estado activo/inactivo
    - Rol de administrador
    - Estado de verificación de email
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Usuario no encontrado",
                "error": "USER_NOT_FOUND"
            }
        )
    
    # Prevenir que un admin se quite sus propios permisos
    if user.id == current_user.id and user_data.is_admin is False:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "No puedes quitarte tus propios permisos de administrador",
                "error": "CANNOT_DEMOTE_SELF"
            }
        )
    
    # Actualizar campos
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin
    
    if user_data.email_verified is not None:
        user.email_verified = user_data.email_verified
        if user_data.email_verified and not user.email_verified_at:
            user.email_verified_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Usuario actualizado exitosamente",
        "data": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "email_verified": user.email_verified,
            "email_verified_at": user.email_verified_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    }


@router.post("/admin/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    ban_data: UserBanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Banear usuario (desactivar cuenta) - solo admin.
    
    Desactiva la cuenta del usuario, impidiendo el inicio de sesión.
    Se puede incluir una razón del baneo.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Usuario no encontrado",
                "error": "USER_NOT_FOUND"
            }
        )
    
    # No permitir banear a otros admins
    if user.is_admin:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "No puedes banear a un administrador",
                "error": "CANNOT_BAN_ADMIN"
            }
        )
    
    # No permitir banearse a sí mismo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "No puedes banearte a ti mismo",
                "error": "CANNOT_BAN_SELF"
            }
        )
    
    # Desactivar usuario
    user.is_active = False
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": f"Usuario baneado exitosamente{': ' + ban_data.reason if ban_data.reason else ''}",
        "data": {
            "user_id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "reason": ban_data.reason
        }
    }


@router.post("/admin/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Desbanear usuario (reactivar cuenta) - solo admin.
    
    Reactiva la cuenta del usuario, permitiendo el inicio de sesión.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Usuario no encontrado",
                "error": "USER_NOT_FOUND"
            }
        )
    
    if user.is_active:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El usuario ya está activo",
                "error": "USER_ALREADY_ACTIVE"
            }
        )
    
    # Reactivar usuario
    user.is_active = True
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Usuario desbaneado exitosamente",
        "data": {
            "user_id": str(user.id),
            "email": user.email,
            "is_active": user.is_active
        }
    }


@router.delete("/admin/users/{user_id}")
async def delete_user_admin(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar usuario permanentemente (solo admin).
    
    ⚠️ PRECAUCIÓN: Esta acción es IRREVERSIBLE.
    Elimina el usuario y todas sus relaciones (órdenes, direcciones, carrito).
    
    Nota: Se recomienda usar ban/unban en su lugar para soft delete.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Usuario no encontrado",
                "error": "USER_NOT_FOUND"
            }
        )
    
    # No permitir eliminar admins
    if user.is_admin:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "No puedes eliminar a un administrador",
                "error": "CANNOT_DELETE_ADMIN"
            }
        )
    
    # No permitir eliminarse a sí mismo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "No puedes eliminarte a ti mismo",
                "error": "CANNOT_DELETE_SELF"
            }
        )
    
    # Eliminar usuario (cascade eliminará órdenes, direcciones, etc.)
    db.delete(user)
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Usuario eliminado permanentemente"
    }


@router.get("/admin/stats")
async def get_user_stats_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener estadísticas generales de usuarios (solo admin).
    
    Incluye:
    - Total de usuarios (activos, inactivos, admins, verificados)
    - Nuevos registros (hoy, esta semana, este mes)
    - Top 10 usuarios con más compras
    """
    # Contadores básicos
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = db.query(User).filter(User.is_active == False).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    verified_users = db.query(User).filter(User.email_verified == True).count()
    unverified_users = db.query(User).filter(User.email_verified == False).count()
    
    # Nuevos registros
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    new_users_today = db.query(User).filter(User.created_at >= today_start).count()
    new_users_this_week = db.query(User).filter(User.created_at >= week_start).count()
    new_users_this_month = db.query(User).filter(User.created_at >= month_start).count()
    
    # Top 10 usuarios que más han gastado
    top_spenders = db.query(
        User.id,
        User.email,
        User.full_name,
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total).label('total_spent')
    ).join(Order).filter(
        Order.status == OrderStatus.DELIVERED
    ).group_by(User.id).order_by(desc('total_spent')).limit(10).all()
    
    top_spenders_data = [
        {
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "total_orders": user.total_orders,
            "total_spent": float(user.total_spent)
        }
        for user in top_spenders
    ]
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Estadísticas obtenidas exitosamente",
        "data": {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "admin_users": admin_users,
            "verified_users": verified_users,
            "unverified_users": unverified_users,
            "new_users_today": new_users_today,
            "new_users_this_week": new_users_this_week,
            "new_users_this_month": new_users_this_month,
            "top_spenders": top_spenders_data
        }
    }
