"""
Rutas para Protocolos.
IMPORTANTE: Rutas fijas (admin/*, my-protocols/) van ANTES de /{protocol_slug}
para evitar que FastAPI las intercepte como slugs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from core.database import get_db
from core.dependencies import get_current_user
from models.user import User
from models.products import Product
from models.protocols import Protocol, ProtocolPhase, ProtocolAccess, ProtocolProgress, ProtocolCategory, protocol_product_association
from schemas.protocols import (
    ProtocolDetailedResponse,
    ProtocolResponse,
    ProtocolCreate,
    ProtocolUpdate,
    ProtocolPhaseCreate,
    ProtocolPhaseUpdate,
    ProtocolPhaseResponse,
    ProtocolUserAccessResponse,
    ProtocolProgressResponse,
    ProtocolProgressUpdate,
    ProtocolCategoryCreate,
    ProtocolCategoryUpdate,
    ProtocolCategoryResponse,
)

router = APIRouter(
    prefix="/protocols",
    tags=["protocols"]
)


# ==================== HELPER ====================

def _phase_to_dict(phase: ProtocolPhase, include_content: bool = True) -> dict:
    """Serializar fase. Sin include_content solo devuelve metadatos (título, descripción, orden)."""
    d = {
        "id": phase.id,
        "protocol_id": phase.protocol_id,
        "title": phase.title,
        "slug": phase.slug,
        "description": phase.description,
        "order": phase.order,
        "duration_minutes": phase.duration_minutes,
        "is_required": phase.is_required,
        "created_at": phase.created_at,
        "updated_at": phase.updated_at,
        "content": phase.content if include_content else "",
        "resources": [
            {
                "id": r.id,
                "phase_id": r.phase_id,
                "resource_type": r.resource_type,
                "title": r.title,
                "description": r.description,
                "url": r.url,
                "file_path": r.file_path,
                "order": r.order,
                "is_visible": r.is_visible,
                "created_at": r.created_at,
            }
            for r in phase.resources
        ] if include_content else [],
    }
    return d


def _protocol_to_dict(protocol: Protocol, include_phases: bool = False, include_phase_content: bool = True) -> dict:
    """Serializar protocolo a dict con campos comunes.
    include_phase_content=False para endpoints públicos de protocolos de pago.
    """
    category_dict = None
    if protocol.category:
        category_dict = {
            "id": protocol.category.id,
            "name": protocol.category.name,
            "slug": protocol.category.slug,
            "is_active": protocol.category.is_active,
            "created_at": protocol.category.created_at,
            "updated_at": protocol.category.updated_at,
        }

    data = {
        "id": protocol.id,
        "name": protocol.name,
        "slug": protocol.slug,
        "description": protocol.description,
        "long_description": protocol.long_description,
        "price": float(protocol.price),
        "image_url": protocol.image_url,
        "product_id": protocol.product_id,
        "author": protocol.author,
        "category_id": protocol.category_id,
        "category": category_dict,
        "version": protocol.version,
        "estimated_duration_hours": protocol.estimated_duration_hours,
        "is_published": protocol.is_published,
        "is_featured": protocol.is_featured,
        "associated_products": [
            {"id": p.id, "name": p.name, "slug": p.slug, "image_url": p.image_url}
            for p in protocol.associated_products
        ],
        "associated_product_ids": [p.id for p in protocol.associated_products],
        "created_at": protocol.created_at,
        "updated_at": protocol.updated_at,
    }
    if include_phases:
        data["phases"] = [_phase_to_dict(ph, include_content=include_phase_content) for ph in protocol.phases]
        data["total_phases"] = len(protocol.phases)
        total_duration = sum([ph.duration_minutes or 0 for ph in protocol.phases])
        data["total_duration_hours"] = total_duration / 60 if total_duration > 0 else None
    else:
        data["total_phases"] = len(protocol.phases)
    return data


# ==================== ADMIN ENDPOINTS - CATEGORIES ====================

@router.post("/admin/categories")
async def create_category(
    category_data: ProtocolCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crear nueva categoría de protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    # Verificar que no exista una categoría con el mismo nombre o slug
    existing_name = db.query(ProtocolCategory).filter(ProtocolCategory.name == category_data.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Ya existe una categoría con ese nombre")
    
    existing_slug = db.query(ProtocolCategory).filter(ProtocolCategory.slug == category_data.slug).first()
    if existing_slug:
        raise HTTPException(status_code=400, detail="Ya existe una categoría con ese slug")
    
    category = ProtocolCategory(
        name=category_data.name,
        slug=category_data.slug,
        is_active=category_data.is_active,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Categoría creada exitosamente",
        "data": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "is_active": category.is_active,
            "created_at": category.created_at,
        }
    }


@router.get("/admin/categories")
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Listar todas las categorías de protocolos (admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    categories = db.query(ProtocolCategory).order_by(ProtocolCategory.name).all()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categorías obtenidas",
        "data": {
            "categories": [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "slug": cat.slug,
                    "is_active": cat.is_active,
                    "created_at": cat.created_at,
                    "updated_at": cat.updated_at,
                    "protocol_count": len(cat.protocols)
                }
                for cat in categories
            ]
        }
    }


@router.get("/admin/categories/{category_id}")
async def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener detalle de una categoría (admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    category = db.query(ProtocolCategory).filter(ProtocolCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categoría obtenida",
        "data": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "is_active": category.is_active,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
            "protocols": [
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "is_published": p.is_published
                }
                for p in category.protocols
            ]
        }
    }


@router.put("/admin/categories/{category_id}")
async def update_category(
    category_id: int,
    category_data: ProtocolCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar categoría de protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    category = db.query(ProtocolCategory).filter(ProtocolCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    update_data = category_data.dict(exclude_unset=True)
    
    # Verificar unicidad de nombre si se está actualizando
    if "name" in update_data:
        existing = db.query(ProtocolCategory).filter(
            ProtocolCategory.name == update_data["name"],
            ProtocolCategory.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe otra categoría con ese nombre")
    
    # Verificar unicidad de slug si se está actualizando
    if "slug" in update_data:
        existing = db.query(ProtocolCategory).filter(
            ProtocolCategory.slug == update_data["slug"],
            ProtocolCategory.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe otra categoría con ese slug")
    
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categoría actualizada",
        "data": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "is_active": category.is_active,
            "updated_at": category.updated_at,
        }
    }


@router.delete("/admin/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Eliminar categoría de protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    category = db.query(ProtocolCategory).filter(ProtocolCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    # Verificar que no haya protocolos asociados
    if category.protocols:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar: hay {len(category.protocols)} protocolo(s) asociado(s)")
    
    db.delete(category)
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categoría eliminada"
    }


# ==================== ADMIN ENDPOINTS (rutas fijas primero) ====================

@router.get("/admin/all")
async def admin_list_protocols(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = Query(None),
    featured_only: bool = Query(False),
    is_published: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Listar todos los protocolos (admin) - incluye borradores."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    query = db.query(Protocol)
    if is_published is not None:
        query = query.filter(Protocol.is_published == is_published)
    if featured_only:
        query = query.filter(Protocol.is_featured == True)
    if category_id:
        query = query.filter(Protocol.category_id == category_id)
    
    total = query.count()
    total_pages = max(1, -(-total // limit))
    offset = (page - 1) * limit
    protocols = query.order_by(desc(Protocol.created_at)).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Protocolos obtenidos",
        "data": {
            "protocols": [_protocol_to_dict(p, include_phases=True) for p in protocols],
            "pagination": {
                "page": page, "limit": limit, "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages, "has_prev": page > 1,
            }
        }
    }


def _get_or_create_digital_category(db: Session):
    """Obtener o crear la categoría de productos digitales."""
    from models.products import Category as ProductCategory
    category = db.query(ProductCategory).filter(
        ProductCategory.slug == "protocolos-digitales"
    ).first()
    if not category:
        category = ProductCategory(
            name="Protocolos Digitales",
            slug="protocolos-digitales",
            description="Protocolos y cursos digitales",
            is_active=True,
        )
        db.add(category)
        db.flush()
    return category


def _create_digital_product_for_protocol(db: Session, name: str, slug: str, description: str, price: Decimal, image_url) -> Product:
    """Crear un producto digital vinculado al protocolo."""
    digital_category = _get_or_create_digital_category(db)
    product_slug = f"protocolo-{slug}"
    # Garantizar slug único
    if db.query(Product).filter(Product.slug == product_slug).first():
        import time
        product_slug = f"protocolo-{slug}-{int(time.time())}"
    product = Product(
        name=name,
        slug=product_slug,
        description=description or name,
        price=price,
        stock=0,
        category_id=digital_category.id,
        image_url=image_url,
        is_active=True,
        is_digital=True,
    )
    db.add(product)
    db.flush()
    return product


@router.post("/admin/create")
async def create_protocol(
    protocol_data: ProtocolCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crear nuevo protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")

    # Verificar categoría
    category = db.query(ProtocolCategory).filter(ProtocolCategory.id == protocol_data.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    # Verificar slug único
    existing = db.query(Protocol).filter(Protocol.slug == protocol_data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un protocolo con ese slug")

    # Resolver product_id: si no se provee, crear un producto digital automáticamente
    product_id = protocol_data.product_id
    if not product_id:
        digital_product = _create_digital_product_for_protocol(
            db,
            name=protocol_data.name,
            slug=protocol_data.slug,
            description=protocol_data.description,
            price=Decimal(str(protocol_data.price)),
            image_url=protocol_data.image_url,
        )
        product_id = digital_product.id

    protocol = Protocol(
        name=protocol_data.name,
        slug=protocol_data.slug,
        description=protocol_data.description,
        long_description=protocol_data.long_description,
        price=Decimal(str(protocol_data.price)),
        image_url=protocol_data.image_url,
        product_id=product_id,
        category_id=protocol_data.category_id,
        author=protocol_data.author,
        version=protocol_data.version,
        estimated_duration_hours=protocol_data.estimated_duration_hours,
        is_featured=protocol_data.is_featured,
        is_published=False,
    )
    db.add(protocol)
    db.flush()

    # Productos asociados
    if protocol_data.associated_product_ids:
        assoc_products = db.query(Product).filter(
            Product.id.in_(protocol_data.associated_product_ids)
        ).all()
        protocol.associated_products = assoc_products
    
    # Fases
    for i, phase_data in enumerate(protocol_data.phases or []):
        phase = ProtocolPhase(
            protocol_id=protocol.id,
            title=phase_data.title,
            slug=phase_data.slug,
            description=phase_data.description,
            content=phase_data.content,
            order=phase_data.order if phase_data.order is not None else i,
            duration_minutes=phase_data.duration_minutes,
            is_required=phase_data.is_required,
        )
        db.add(phase)
    
    db.commit()
    db.refresh(protocol)
    
    return _protocol_to_dict(protocol, include_phases=True)


@router.put("/admin/{protocol_id}")
async def update_protocol(
    protocol_id: int,
    protocol_data: ProtocolUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")
    
    update_data = protocol_data.dict(exclude_unset=True)
    
    # Manejar productos asociados por separado
    associated_ids = update_data.pop("associated_product_ids", None)
    if associated_ids is not None:
        assoc_products = db.query(Product).filter(Product.id.in_(associated_ids)).all()
        protocol.associated_products = assoc_products
    
    # Actualizar campos escalares
    for field, value in update_data.items():
        if field == "price" and value is not None:
            value = Decimal(str(value))
        setattr(protocol, field, value)

    # Sincronizar producto digital vinculado (solo si fue auto-creado: is_digital=True)
    if protocol.product_id:
        linked_product = db.query(Product).filter(
            Product.id == protocol.product_id,
            Product.is_digital == True
        ).first()
        if linked_product:
            if "price" in update_data:
                linked_product.price = Decimal(str(update_data["price"]))
            if "name" in update_data:
                linked_product.name = update_data["name"]
            if "image_url" in update_data:
                linked_product.image_url = update_data["image_url"]

    db.commit()
    db.refresh(protocol)

    return _protocol_to_dict(protocol, include_phases=True)


@router.put("/admin/{protocol_id}/publish")
async def publish_protocol(
    protocol_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publicar un protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")
    if not protocol.phases:
        raise HTTPException(status_code=400, detail="El protocolo debe tener al menos una fase")
    
    protocol.is_published = True
    db.commit()
    return {"success": True, "status_code": 200, "message": f"Protocolo '{protocol.name}' publicado", "data": {"protocol_id": protocol.id}}


@router.put("/admin/{protocol_id}/unpublish")
async def unpublish_protocol(
    protocol_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Despublicar un protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")
    
    protocol.is_published = False
    db.commit()
    return {"success": True, "status_code": 200, "message": f"Protocolo '{protocol.name}' despublicado", "data": {"protocol_id": protocol.id}}


@router.post("/admin/sync-products")
async def sync_protocol_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crear productos digitales para protocolos que no tienen product_id (migración)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")

    orphan_protocols = db.query(Protocol).filter(Protocol.product_id == None).all()
    created = []
    for protocol in orphan_protocols:
        digital_product = _create_digital_product_for_protocol(
            db,
            name=protocol.name,
            slug=protocol.slug,
            description=protocol.description or protocol.name,
            price=Decimal(str(protocol.price)),
            image_url=protocol.image_url,
        )
        protocol.product_id = digital_product.id
        created.append({"protocol_id": protocol.id, "protocol_name": protocol.name, "product_id": digital_product.id})

    db.commit()
    return {
        "success": True,
        "status_code": 200,
        "message": f"{len(created)} protocolo(s) sincronizados",
        "data": {"synced": created}
    }


@router.delete("/admin/{protocol_id}")
async def delete_protocol(
    protocol_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Eliminar protocolo permanentemente (solo admin).
    Bloqueado si algún usuario ya lo compró — en ese caso solo se puede desactivar/despublicar.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")

    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")

    has_purchases = db.query(ProtocolAccess).filter(
        ProtocolAccess.protocol_id == protocol_id
    ).first()
    if has_purchases:
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "status_code": 409,
                "message": "No se puede eliminar un protocolo que ya fue comprado. Usa 'Despublicar' para ocultarlo.",
                "error": "PROTOCOL_HAS_PURCHASES"
            }
        )

    db.delete(protocol)
    db.commit()
    return {"success": True, "status_code": 200, "message": "Protocolo eliminado"}


# ==================== ADMIN ENDPOINTS - PHASES ====================

@router.post("/admin/{protocol_id}/phases")
async def create_phase(
    protocol_id: int,
    phase_data: ProtocolPhaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crear una nueva fase en un protocolo existente (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")
    
    # Verificar slug único dentro del protocolo
    existing_slug = db.query(ProtocolPhase).filter(
        ProtocolPhase.protocol_id == protocol_id,
        ProtocolPhase.slug == phase_data.slug
    ).first()
    if existing_slug:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una fase con ese slug en este protocolo"
        )
    
    # Determinar el orden
    max_order = db.query(ProtocolPhase).filter(
        ProtocolPhase.protocol_id == protocol_id
    ).order_by(ProtocolPhase.order.desc()).first()
    next_order = (max_order.order + 1) if max_order else 0
    
    phase = ProtocolPhase(
        protocol_id=protocol_id,
        title=phase_data.title,
        slug=phase_data.slug,
        description=phase_data.description,
        content=phase_data.content,
        order=phase_data.order if phase_data.order is not None else next_order,
        duration_minutes=phase_data.duration_minutes,
        is_required=phase_data.is_required,
    )
    db.add(phase)
    db.flush()
    
    # Agregar recursos si existen
    if phase_data.resources:
        for resource_data in phase_data.resources:
            from models.protocols import ProtocolResource
            resource = ProtocolResource(
                phase_id=phase.id,
                resource_type=resource_data.resource_type,
                title=resource_data.title,
                description=resource_data.description,
                url=resource_data.url,
                order=resource_data.order,
                is_visible=resource_data.is_visible,
            )
            db.add(resource)
    
    db.commit()
    db.refresh(phase)
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Fase creada exitosamente",
        "data": {
            "id": phase.id,
            "protocol_id": phase.protocol_id,
            "title": phase.title,
            "slug": phase.slug,
            "description": phase.description,
            "content": phase.content,
            "order": phase.order,
            "duration_minutes": phase.duration_minutes,
            "is_required": phase.is_required,
            "created_at": phase.created_at,
        }
    }


@router.put("/admin/{protocol_id}/phases/{phase_id}")
async def update_phase(
    protocol_id: int,
    phase_id: int,
    phase_data: ProtocolPhaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar una fase específica del protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")
    
    phase = db.query(ProtocolPhase).filter(
        ProtocolPhase.id == phase_id,
        ProtocolPhase.protocol_id == protocol_id
    ).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Fase no encontrada en este protocolo")
    
    update_data = phase_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(phase, field, value)
    
    db.commit()
    db.refresh(phase)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Fase actualizada exitosamente",
        "data": {
            "id": phase.id,
            "protocol_id": phase.protocol_id,
            "title": phase.title,
            "slug": phase.slug,
            "description": phase.description,
            "content": phase.content,
            "order": phase.order,
            "duration_minutes": phase.duration_minutes,
            "is_required": phase.is_required,
            "updated_at": phase.updated_at,
        }
    }


@router.delete("/admin/{protocol_id}/phases/{phase_id}")
async def delete_phase(
    protocol_id: int,
    phase_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Eliminar una fase específica del protocolo (solo admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    protocol = db.query(Protocol).filter(Protocol.id == protocol_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")
    
    phase = db.query(ProtocolPhase).filter(
        ProtocolPhase.id == phase_id,
        ProtocolPhase.protocol_id == protocol_id
    ).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Fase no encontrada en este protocolo")
    
    # Verificar que no sea la única fase si el protocolo está publicado
    if protocol.is_published and len(protocol.phases) == 1:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar la única fase de un protocolo publicado"
        )
    
    phase_title = phase.title
    db.delete(phase)
    
    # Reordenar las fases restantes
    remaining_phases = db.query(ProtocolPhase).filter(
        ProtocolPhase.protocol_id == protocol_id
    ).order_by(ProtocolPhase.order).all()
    for idx, p in enumerate(remaining_phases):
        p.order = idx
    
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": f"Fase '{phase_title}' eliminada exitosamente"
    }


# ==================== USER ENDPOINTS (rutas fijas) ====================

@router.get("/my-protocols/", response_model=List[ProtocolUserAccessResponse])
async def get_my_protocols(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener protocolos comprados del usuario."""
    accesses = db.query(ProtocolAccess).filter(
        ProtocolAccess.user_id == current_user.id,
        ProtocolAccess.is_active == True
    ).all()
    
    if not accesses:
        return []
    
    result = []
    for access in accesses:
        progress = db.query(ProtocolProgress).filter(
            ProtocolProgress.protocol_id == access.protocol_id,
            ProtocolProgress.user_id == current_user.id
        ).first()
        result.append({
            "protocol_id": access.protocol_id,
            "protocol_name": access.protocol.name,
            "protocol_slug": access.protocol.slug,
            "access_granted_at": access.granted_at,
            "access_until": access.access_until,
            "current_progress": progress
        })
    return result


# ==================== PUBLIC ENDPOINTS ====================

@router.get("/categories")
async def list_public_categories(db: Session = Depends(get_db)):
    """Listar categorías de protocolos activas (público)."""
    categories = db.query(ProtocolCategory).filter(
        ProtocolCategory.is_active == True
    ).order_by(ProtocolCategory.name).all()
    return {
        "success": True,
        "status_code": 200,
        "message": "Categorías obtenidas",
        "data": {
            "categories": [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "slug": cat.slug,
                    "is_active": cat.is_active,
                    "created_at": cat.created_at,
                    "updated_at": cat.updated_at,
                }
                for cat in categories
            ]
        }
    }


@router.get("/")
async def list_protocols(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    category_id: Optional[int] = Query(None),
    featured_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Listar protocolos publicados (público)."""
    query = db.query(Protocol).filter(Protocol.is_published == True)
    if featured_only:
        query = query.filter(Protocol.is_featured == True)
    if category_id:
        query = query.filter(Protocol.category_id == category_id)
    if search:
        query = query.filter(Protocol.name.ilike(f"%{search}%"))

    total = query.count()
    total_pages = max(1, -(-total // limit))
    offset = (page - 1) * limit
    protocols = query.order_by(desc(Protocol.is_featured), desc(Protocol.created_at)).offset(offset).limit(limit).all()

    result = []
    for protocol in protocols:
        category_dict = None
        if protocol.category:
            category_dict = {
                "id": protocol.category.id,
                "name": protocol.category.name,
                "slug": protocol.category.slug,
                "is_active": protocol.category.is_active,
                "created_at": protocol.category.created_at,
                "updated_at": protocol.category.updated_at,
            }

        result.append({
            "id": protocol.id,
            "name": protocol.name,
            "slug": protocol.slug,
            "description": protocol.description,
            "author": protocol.author,
            "category": category_dict,
            "estimated_duration_hours": protocol.estimated_duration_hours,
            "is_featured": protocol.is_featured,
            "total_phases": len(protocol.phases),
            "price": float(protocol.price),
            "image_url": protocol.image_url,
            "product_id": protocol.product_id,
        })

    return {
        "success": True,
        "status_code": 200,
        "message": "Protocolos obtenidos",
        "data": {
            "protocols": result,
            "pagination": {
                "page": page, "limit": limit, "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }
    }


# ==================== WILDCARD SLUG ENDPOINTS (al final) ====================

@router.get("/{protocol_slug}")
async def get_protocol(
    protocol_slug: str,
    db: Session = Depends(get_db)
):
    """Detalle público de un protocolo publicado.
    Devuelve metadatos de fases pero NO el contenido HTML (protocolos de pago).
    Los protocolos gratuitos (price=0) sí exponen el contenido completo.
    """
    protocol = db.query(Protocol).filter(
        Protocol.slug == protocol_slug,
        Protocol.is_published == True
    ).first()
    if not protocol:
        raise HTTPException(status_code=404, detail={"success": False, "status_code": 404, "message": "Protocolo no encontrado", "error": "PROTOCOL_NOT_FOUND"})

    is_free = float(protocol.price) == 0
    return _protocol_to_dict(protocol, include_phases=True, include_phase_content=is_free)


@router.get("/{protocol_slug}/read")
async def read_protocol(
    protocol_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leer protocolo completo (solo usuarios con acceso)."""
    protocol = db.query(Protocol).filter(Protocol.slug == protocol_slug).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")
    
    access = db.query(ProtocolAccess).filter(
        ProtocolAccess.protocol_id == protocol.id,
        ProtocolAccess.user_id == current_user.id,
        ProtocolAccess.is_active == True
    ).first()
    if not access:
        raise HTTPException(status_code=403, detail={"success": False, "status_code": 403, "message": "No tienes acceso a este protocolo", "error": "PROTOCOL_ACCESS_DENIED"})
    
    access.last_accessed_at = datetime.utcnow()
    progress = db.query(ProtocolProgress).filter(
        ProtocolProgress.protocol_id == protocol.id,
        ProtocolProgress.user_id == current_user.id
    ).first()
    if progress:
        progress.last_accessed_at = datetime.utcnow()
    db.commit()
    
    return _protocol_to_dict(protocol, include_phases=True)


@router.put("/{protocol_slug}/progress", response_model=ProtocolProgressResponse)
async def update_protocol_progress(
    protocol_slug: str,
    progress_data: ProtocolProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar progreso del usuario en un protocolo."""
    protocol = db.query(Protocol).filter(Protocol.slug == protocol_slug).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocolo no encontrado")
    
    access = db.query(ProtocolAccess).filter(
        ProtocolAccess.protocol_id == protocol.id,
        ProtocolAccess.user_id == current_user.id,
        ProtocolAccess.is_active == True
    ).first()
    if not access:
        raise HTTPException(status_code=403, detail="No tienes acceso a este protocolo")
    
    progress = db.query(ProtocolProgress).filter(
        ProtocolProgress.protocol_id == protocol.id,
        ProtocolProgress.user_id == current_user.id
    ).first()
    if not progress:
        progress = ProtocolProgress(
            protocol_id=protocol.id,
            user_id=current_user.id,
            total_phases=len(protocol.phases)
        )
        db.add(progress)
    
    progress.current_phase_order = progress_data.current_phase_order
    progress.completed_phases = progress_data.completed_phases
    progress.last_accessed_at = datetime.utcnow()
    if progress.completed_phases >= progress.total_phases:
        progress.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(progress)
    return progress
