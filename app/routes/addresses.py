"""
Endpoints para gestión de direcciones de entrega.
Límite: 3 direcciones por usuario.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.dependencies import get_current_user
from models.user import User
from models.addresses import Address
from schemas.addresses import (
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    AddressListResponse
)

router = APIRouter(
    prefix="/addresses",
    tags=["addresses"]
)

# Constante: máximo de direcciones por usuario
MAX_ADDRESSES = 3


def format_address_response(address: Address) -> dict:
    """Formatear dirección para respuesta"""
    return {
        "id": address.id,
        "user_id": str(address.user_id),
        "full_name": address.full_name,
        "phone": address.phone,
        "rfc": address.rfc,
        "label": address.label,
        "street": address.street,
        "city": address.city,
        "state": address.state,
        "postal_code": address.postal_code,
        "country": address.country,
        "is_default": address.is_default,
        "created_at": address.created_at.isoformat() if address.created_at else None
    }


# ==================== ENDPOINTS ====================

@router.get("/", response_model=None)
async def get_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener todas las direcciones del usuario autenticado.
    
    - Retorna hasta 3 direcciones
    - Ordenadas por is_default y fecha de creación
    """
    addresses = db.query(Address).filter(
        Address.user_id == current_user.id
    ).order_by(
        Address.is_default.desc(),
        Address.created_at.desc()
    ).all()
    
    addresses_data = [format_address_response(addr) for addr in addresses]
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Direcciones obtenidas exitosamente",
        "data": {
            "addresses": addresses_data,
            "total": len(addresses_data),
            "max_addresses": MAX_ADDRESSES
        }
    }


@router.get("/{address_id}")
async def get_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener una dirección específica del usuario.
    """
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()
    
    if not address:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Dirección no encontrada",
                "error": "ADDRESS_NOT_FOUND"
            }
        )
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Dirección obtenida exitosamente",
        "data": format_address_response(address)
    }


@router.post("/", status_code=201)
async def create_address(
    address_data: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear nueva dirección de entrega.
    
    - Límite: 3 direcciones por usuario
    - Si es la primera dirección, se marca como predeterminada automáticamente
    - Si se marca como predeterminada, se actualiza la anterior
    """
    # Verificar límite de direcciones
    addresses_count = db.query(Address).filter(
        Address.user_id == current_user.id
    ).count()
    
    if addresses_count >= MAX_ADDRESSES:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"Has alcanzado el límite de {MAX_ADDRESSES} direcciones",
                "error": "MAX_ADDRESSES_REACHED"
            }
        )
    
    # Si es la primera dirección, marcarla como predeterminada
    if addresses_count == 0:
        address_data.is_default = True
    
    # Si se marca como predeterminada, quitar el flag de otras direcciones
    if address_data.is_default:
        db.query(Address).filter(
            Address.user_id == current_user.id,
            Address.is_default == True
        ).update({"is_default": False})
        db.commit()
    
    # Crear nueva dirección
    new_address = Address(
        user_id=current_user.id,
        full_name=address_data.full_name,
        phone=address_data.phone,
        rfc=address_data.rfc,
        label=address_data.label,
        street=address_data.street,
        city=address_data.city,
        state=address_data.state,
        postal_code=address_data.postal_code,
        country=address_data.country,
        is_default=address_data.is_default
    )
    
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Dirección creada exitosamente",
        "data": format_address_response(new_address)
    }


@router.put("/{address_id}")
async def update_address(
    address_id: int,
    address_data: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar una dirección existente.
    
    - Solo se pueden actualizar las direcciones del usuario autenticado
    - Si se marca como predeterminada, se actualiza la anterior
    """
    # Buscar dirección
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()
    
    if not address:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Dirección no encontrada",
                "error": "ADDRESS_NOT_FOUND"
            }
        )
    
    # Si se marca como predeterminada, quitar el flag de otras direcciones
    if address_data.is_default and not address.is_default:
        db.query(Address).filter(
            Address.user_id == current_user.id,
            Address.id != address_id,
            Address.is_default == True
        ).update({"is_default": False})
    
    # Actualizar campos que se proporcionaron
    update_data = address_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(address, field, value)
    
    db.commit()
    db.refresh(address)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Dirección actualizada exitosamente",
        "data": format_address_response(address)
    }


@router.delete("/{address_id}")
async def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar una dirección.
    
    - Solo se pueden eliminar las direcciones del usuario autenticado
    - Si se elimina la dirección predeterminada, se marca otra como predeterminada
    """
    # Buscar dirección
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()
    
    if not address:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Dirección no encontrada",
                "error": "ADDRESS_NOT_FOUND"
            }
        )
    
    was_default = address.is_default
    
    # Eliminar dirección
    db.delete(address)
    db.commit()
    
    # Si era la predeterminada, marcar otra como predeterminada
    if was_default:
        remaining_address = db.query(Address).filter(
            Address.user_id == current_user.id
        ).first()
        
        if remaining_address:
            remaining_address.is_default = True
            db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Dirección eliminada exitosamente",
        "data": None
    }


@router.patch("/{address_id}/set-default")
async def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marcar una dirección como predeterminada.
    
    - Solo se puede marcar una dirección del usuario autenticado
    - Se actualiza la dirección predeterminada anterior
    """
    # Buscar dirección
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()
    
    if not address:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Dirección no encontrada",
                "error": "ADDRESS_NOT_FOUND"
            }
        )
    
    # Si ya es la predeterminada, no hacer nada
    if address.is_default:
        return {
            "success": True,
            "status_code": 200,
            "message": "Esta dirección ya es la predeterminada",
            "data": format_address_response(address)
        }
    
    # Quitar el flag de otras direcciones
    db.query(Address).filter(
        Address.user_id == current_user.id,
        Address.is_default == True
    ).update({"is_default": False})
    
    # Marcar esta como predeterminada
    address.is_default = True
    db.commit()
    db.refresh(address)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Dirección marcada como predeterminada",
        "data": format_address_response(address)
    }
