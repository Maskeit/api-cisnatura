from fastapi import APIRouter, Depends, Query, HTTPException


from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from models.products import Product, Category
from decimal import Decimal
from core.dependencies import get_current_admin_user
from models.user import User

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

# listar productos con paginación y filtros primeros 10
@router.get("/")
async def list_products(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Items por página"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoría"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    min_price: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[float] = Query(None, ge=0, description="Precio máximo"),
    db: Session = Depends(get_db)
):
    """
    Listar productos con paginación y filtros.
    
    - **page**: Número de página (default: 1)
    - **limit**: Productos por página (default: 10, max: 100)
    - **category_id**: Filtrar por ID de categoría
    - **search**: Buscar en nombre del producto
    - **min_price**: Precio mínimo
    - **max_price**: Precio máximo
    """
    # Construir query base
    query = db.query(Product).filter(Product.is_active == True)
    
    # Aplicar filtros
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    if min_price is not None:
        query = query.filter(Product.price >= Decimal(str(min_price)))
    
    if max_price is not None:
        query = query.filter(Product.price <= Decimal(str(max_price)))
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    
    # Calcular metadata de paginación
    total_pages = (total + limit - 1) // limit
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Productos obtenidos exitosamente",
        "data": {
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "description": p.description,
                    "price": float(p.price),
                    "stock": p.stock,
                    "category_id": p.category_id,
                    "image_url": p.image_url,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in products
            ],
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

# Obtener producto por ID
@router.get("/{product_id}")
async def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener un producto por su ID.
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado",
                "error": "PRODUCT_NOT_FOUND"
            }
        )
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Producto obtenido exitosamente",
        "data": {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "price": float(product.price),
            "stock": product.stock,
            "category_id": product.category_id,
            "image_url": product.image_url,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }
    }

# Obtener producto por slug (descripcion amigable)
@router.get("/slug/{slug}")
async def get_product_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Obtener un producto por su slug (para URLs amigables).
    """
    product = db.query(Product).filter(
        Product.slug == slug,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado",
                "error": "PRODUCT_NOT_FOUND"
            }
        )
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Producto obtenido exitosamente",
        "data": {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "price": float(product.price),
            "stock": product.stock,
            "category_id": product.category_id,
            "image_url": product.image_url,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }
    }
    
    
# ==================== ADMIN ENDPOINTS ====================
# Requieren autenticación y rol de administrador

# Endpoint para listar TODOS los productos (admin)
@router.get("/admin/all")
async def list_all_products_admin(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Items por página"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoría"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    min_price: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[float] = Query(None, ge=0, description="Precio máximo"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Listar TODOS los productos con paginación y filtros (solo administradores).
    Muestra productos activos e inactivos.
    
    Requiere autenticación y rol de administrador.
    """
    # Verificar que el usuario sea administrador
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "status_code": 403,
                "message": "No tienes permisos para acceder a este recurso",
                "error": "FORBIDDEN"
            }
        )
    
    # Construir query base (SIN filtrar por is_active)
    query = db.query(Product)
    
    # Aplicar filtros
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    if min_price is not None:
        query = query.filter(Product.price >= Decimal(str(min_price)))
    
    if max_price is not None:
        query = query.filter(Product.price <= Decimal(str(max_price)))
    
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    
    # Calcular metadata de paginación
    total_pages = (total + limit - 1) // limit
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Productos obtenidos exitosamente",
        "data": {
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "description": p.description,
                    "price": float(p.price),
                    "stock": p.stock,
                    "category_id": p.category_id,
                    "image_url": p.image_url,
                    "is_active": p.is_active,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                }
                for p in products
            ],
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


@router.post("/", status_code=201)
async def create_product(
    name: str,
    slug: str,
    description: str,
    price: float,
    stock: int,
    category_id: int,
    image_url: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Crear un nuevo producto (solo administradores).
    
    Requiere autenticación y rol de administrador.
    """
    # Verificar que el usuario sea administrador
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "status_code": 403,
                "message": "No tienes permisos para realizar esta acción",
                "error": "FORBIDDEN"
            }
        )
    
    # Validar que el slug no exista
    existing_product = db.query(Product).filter(Product.slug == slug).first()
    if existing_product:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El slug ya existe",
                "error": "DUPLICATE_SLUG"
            }
        )
    
    # Validar que la categoría exista
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Categoría no encontrada",
                "error": "CATEGORY_NOT_FOUND"
            }
        )
    
    # Validar precio y stock
    if price <= 0:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El precio debe ser mayor a 0",
                "error": "VALIDATION_ERROR"
            }
        )
    
    if stock < 0:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El stock no puede ser negativo",
                "error": "VALIDATION_ERROR"
            }
        )
    
    # Crear el producto
    new_product = Product(
        name=name,
        slug=slug,
        description=description,
        price=Decimal(str(price)),
        stock=stock,
        category_id=category_id,
        image_url=image_url,
        is_active=True
    )
    
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Producto creado exitosamente",
        "data": {
            "id": new_product.id,
            "name": new_product.name,
            "slug": new_product.slug,
            "description": new_product.description,
            "price": float(new_product.price),
            "stock": new_product.stock,
            "category_id": new_product.category_id,
            "image_url": new_product.image_url,
            "is_active": new_product.is_active,
            "created_at": new_product.created_at.isoformat() if new_product.created_at else None
        }
    }


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[float] = None,
    stock: Optional[int] = None,
    category_id: Optional[int] = None,
    image_url: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar un producto existente (solo administradores).
    
    Requiere autenticación y rol de administrador.
    Solo se actualizan los campos enviados.
    """
    # Verificar que el usuario sea administrador
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "status_code": 403,
                "message": "No tienes permisos para realizar esta acción",
                "error": "FORBIDDEN"
            }
        )
    
    # Buscar el producto
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado",
                "error": "PRODUCT_NOT_FOUND"
            }
        )
    
    # Validar slug único si se está actualizando
    if slug and slug != product.slug:
        existing_product = db.query(Product).filter(Product.slug == slug).first()
        if existing_product:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": "El slug ya existe",
                    "error": "DUPLICATE_SLUG"
                }
            )
        product.slug = slug
    
    # Validar categoría si se está actualizando
    if category_id and category_id != product.category_id:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "status_code": 404,
                    "message": "Categoría no encontrada",
                    "error": "CATEGORY_NOT_FOUND"
                }
            )
        product.category_id = category_id
    
    # Actualizar campos opcionales
    if name is not None:
        product.name = name
    
    if description is not None:
        product.description = description
    
    if price is not None:
        if price <= 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": "El precio debe ser mayor a 0",
                    "error": "VALIDATION_ERROR"
                }
            )
        product.price = Decimal(str(price))
    
    if stock is not None:
        if stock < 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": "El stock no puede ser negativo",
                    "error": "VALIDATION_ERROR"
                }
            )
        product.stock = stock
    
    if image_url is not None:
        product.image_url = image_url
    
    if is_active is not None:
        product.is_active = is_active
    
    db.commit()
    db.refresh(product)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Producto actualizado exitosamente",
        "data": {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "price": float(product.price),
            "stock": product.stock,
            "category_id": product.category_id,
            "image_url": product.image_url,
            "is_active": product.is_active,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }
    }


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar un producto (soft delete - solo desactiva).
    Solo administradores.
    
    Requiere autenticación y rol de administrador.
    """
    # Verificar que el usuario sea administrador
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "status_code": 403,
                "message": "No tienes permisos para realizar esta acción",
                "error": "FORBIDDEN"
            }
        )
    
    # Buscar el producto
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "status_code": 404,
                "message": "Producto no encontrado",
                "error": "PRODUCT_NOT_FOUND"
            }
        )
    
    # Soft delete: solo desactivar el producto
    product.is_active = False
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Producto eliminado exitosamente",
        "data": {
            "id": product.id,
            "name": product.name,
            "is_active": product.is_active
        }
    }
