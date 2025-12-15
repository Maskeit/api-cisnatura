from fastapi import APIRouter, Depends, Query, HTTPException


from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from core.database import get_db
from models.products import Product, Category
from decimal import Decimal
from core.dependencies import get_current_admin_user
from models.user import User
from schemas.products import ProductCreate, ProductUpdate, CategoryCreate, CategoryUpdate
from core.storage import storage_service

router = APIRouter(
    prefix="/products",
    tags=["products"]
)


# ==================== CATEGORÍAS ====================

@router.get("/categories")
async def list_categories(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(50, ge=1, le=100, description="Items por página"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    db: Session = Depends(get_db)
):
    """
    Listar categorías activas con paginación.
    
    - **page**: Número de página (default: 1)
    - **limit**: Categorías por página (default: 50, max: 100)
    - **search**: Buscar en nombre de categoría
    - **is_active**: Filtrar por estado (default: solo activas)
    """
    # Construir query base
    query = db.query(Category)
    
    # Por defecto mostrar solo activas (usuarios normales)
    if is_active is None:
        query = query.filter(Category.is_active == True)
    elif is_active is not None:
        query = query.filter(Category.is_active == is_active)
    
    # Aplicar filtros
    if search:
        query = query.filter(Category.name.ilike(f"%{search}%"))
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación
    offset = (page - 1) * limit
    categories = query.offset(offset).limit(limit).all()
    
    # Calcular metadata de paginación
    total_pages = (total + limit - 1) // limit
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categorías obtenidas exitosamente",
        "data": {
            "categories": [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "description": c.description,
                    "image_url": c.image_url,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in categories
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


@router.get("/categories/{category_id}")
async def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener una categoría por su ID.
    """
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.is_active == True
    ).first()
    
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
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categoría obtenida exitosamente",
        "data": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "image_url": category.image_url,
            "created_at": category.created_at.isoformat() if category.created_at else None
        }
    }


@router.post("/categories", status_code=201)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Crear una nueva categoría (solo administradores).
    
    Requiere autenticación y rol de administrador.
    """
    # Verificar que el slug no exista
    existing_category = db.query(Category).filter(Category.slug == category_data.slug).first()
    if existing_category:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El slug ya existe",
                "error": "DUPLICATE_SLUG"
            }
        )
    
    # Verificar que el nombre no exista
    existing_name = db.query(Category).filter(Category.name == category_data.name).first()
    if existing_name:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": "El nombre de categoría ya existe",
                "error": "DUPLICATE_NAME"
            }
        )
    
    # Crear la categoría
    new_category = Category(
        name=category_data.name,
        slug=category_data.slug,
        description=category_data.description,
        image_url=category_data.image_url,
        is_active=True
    )
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return {
        "success": True,
        "status_code": 201,
        "message": "Categoría creada exitosamente",
        "data": {
            "id": new_category.id,
            "name": new_category.name,
            "slug": new_category.slug,
            "description": new_category.description,
            "image_url": new_category.image_url,
            "is_active": new_category.is_active,
            "created_at": new_category.created_at.isoformat() if new_category.created_at else None
        }
    }


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar una categoría existente (solo administradores).
    
    Requiere autenticación y rol de administrador.
    Solo se actualizan los campos enviados.
    """
    # Buscar la categoría
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
    
    # Validar slug único si se está actualizando
    if category_data.slug and category_data.slug != category.slug:
        existing_category = db.query(Category).filter(Category.slug == category_data.slug).first()
        if existing_category:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": "El slug ya existe",
                    "error": "DUPLICATE_SLUG"
                }
            )
        category.slug = category_data.slug
    
    # Validar nombre único si se está actualizando
    if category_data.name and category_data.name != category.name:
        existing_name = db.query(Category).filter(Category.name == category_data.name).first()
        if existing_name:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "status_code": 400,
                    "message": "El nombre de categoría ya existe",
                    "error": "DUPLICATE_NAME"
                }
            )
        category.name = category_data.name
    
    # Actualizar campos opcionales
    if category_data.description is not None:
        category.description = category_data.description
    
    if category_data.image_url is not None:
        # Si hay una imagen antigua, eliminarla antes de asignar la nueva
        if category.image_url:
            storage_service.delete_file(category.image_url)
        category.image_url = category_data.image_url
    
    if category_data.is_active is not None:
        category.is_active = category_data.is_active
    
    db.commit()
    db.refresh(category)
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categoría actualizada exitosamente",
        "data": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "image_url": category.image_url,
            "is_active": category.is_active,
            "created_at": category.created_at.isoformat() if category.created_at else None
        }
    }


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar una categoría (soft delete - solo desactiva).
    Solo administradores.
    
    Requiere autenticación y rol de administrador.
    Nota: No elimina productos asociados, solo desactiva la categoría.
    """
    # Buscar la categoría
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
    
    # Verificar si tiene productos asociados
    products_count = db.query(Product).filter(
        Product.category_id == category_id,
        Product.is_active == True
    ).count()
    
    if products_count > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"No se puede eliminar la categoría porque tiene {products_count} producto(s) activo(s) asociado(s)",
                "error": "CATEGORY_HAS_PRODUCTS"
            }
        )
    
    # Soft delete: solo desactivar la categoría
    # NOTA: No eliminamos la imagen porque puede ser reactivada
    category.is_active = False
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categoría desactivada exitosamente",
        "data": {
            "id": category.id,
            "name": category.name,
            "is_active": category.is_active
        }
    }


@router.delete("/categories/admin/{category_id}/permanent")
async def delete_category_permanent(
    category_id: int,
    force: bool = Query(False, description="Forzar eliminación incluso si tiene productos asociados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar categoría permanentemente (hard delete).
    Solo administradores.
    
    ⚠️ PRECAUCIÓN: Esta acción es IRREVERSIBLE.
    
    Por defecto, NO se puede eliminar una categoría que tenga productos asociados.
    Use el parámetro ?force=true para forzar la eliminación.
    
    Casos de uso:
    - Limpiar categorías de prueba
    - Eliminar categorías duplicadas
    - Eliminar categorías inactivas sin productos
    """
    # Buscar la categoría
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
    
    # Verificar si tiene productos asociados
    products_count = db.query(Product).filter(Product.category_id == category_id).count()
    
    if products_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"No se puede eliminar la categoría porque tiene {products_count} producto(s) asociado(s)",
                "error": "CATEGORY_HAS_PRODUCTS",
                "data": {
                    "products_count": products_count,
                    "suggestion": "Use el parámetro ?force=true para forzar la eliminación"
                }
            }
        )
    
    # Guardar datos antes de eliminar
    category_name = category.name
    category_image = category.image_url
    
    try:
        # Eliminar la categoría permanentemente
        db.delete(category)
        db.commit()
        
        # Eliminar la imagen física del disco
        if category_image:
            storage_service.delete_file(category_image)
        
        return {
            "success": True,
            "status_code": 200,
            "message": "Categoría eliminada permanentemente",
            "data": {
                "id": category_id,
                "name": category_name,
                "had_products": products_count > 0,
                "products_count": products_count
            }
        }
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error eliminando categoría {category_id}: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "status_code": 500,
                "message": "Error al eliminar categoría permanentemente",
                "error": "DATABASE_ERROR",
                "details": str(e)
            }
        )


@router.get("/categories/admin/simple-list")
async def get_categories_simple_list(
    is_active: Optional[bool] = Query(True, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener lista simple de categorías (solo ID y nombre).
    Ideal para desplegables/selects en el panel de admin.
    
    Requiere autenticación y rol de administrador.
    
    - **is_active**: Filtrar por categorías activas (default: True)
    
    Retorna: Lista de objetos con {id, name}
    """
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
    
    # Query base
    query = db.query(Category.id, Category.name)
    
    # Filtrar por estado si se especifica
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)
    
    # Ordenar alfabéticamente
    query = query.order_by(Category.name.asc())
    
    categories = query.all()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Lista de categorías obtenida exitosamente",
        "data": {
            "categories": [
                {
                    "id": str(c.id),  # Como string para consistencia con descuentos
                    "name": c.name
                }
                for c in categories
            ],
            "total": len(categories)
        }
    }


# ==================== PRODUCTOS ====================

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
    Los descuentos activos se aplican automáticamente.
    
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
    
    # Aplicar descuentos a los productos (con descripción truncada)
    from core.discount_service import apply_discounts_to_products
    products_with_discounts = apply_discounts_to_products(
        products, 
        db,
        truncate_description=True,  # Truncar para listados
        max_description_length=150   # Máximo 150 caracteres
    )
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Productos obtenidos exitosamente",
        "data": {
            "products": products_with_discounts,
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
    Aplica descuentos activos automáticamente.
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
    
    # Aplicar descuentos (descripción completa para detalle)
    from core.discount_service import apply_discounts_to_products
    product_with_discount = apply_discounts_to_products(
        [product], 
        db,
        truncate_description=False  # Descripción completa en detalle
    )[0]
    
    # Agregar campos adicionales
    product_with_discount["updated_at"] = product.updated_at.isoformat() if product.updated_at else None
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Producto obtenido exitosamente",
        "data": product_with_discount
    }

# Obtener producto por slug (descripcion amigable)
@router.get("/slug/{slug}")
async def get_product_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Obtener un producto por su slug (para URLs amigables).
    Aplica descuentos activos automáticamente.
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
    
    # Aplicar descuentos (descripción completa para detalle)
    from core.discount_service import apply_discounts_to_products
    product_with_discount = apply_discounts_to_products(
        [product], 
        db,
        truncate_description=False  # Descripción completa en detalle
    )[0]
    
    # Agregar campos adicionales
    product_with_discount["updated_at"] = product.updated_at.isoformat() if product.updated_at else None
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Producto obtenido exitosamente",
        "data": product_with_discount
    }
    
    
# ==================== ADMIN ENDPOINTS ====================
# Requieren autenticación y rol de administrador

# Endpoint para obtener solo IDs y nombres (para desplegables)
@router.get("/admin/simple-list")
async def get_products_simple_list(
    is_active: Optional[bool] = Query(True, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener lista simple de productos (solo ID y nombre).
    Ideal para desplegables/selects en el panel de admin.
    
    Requiere autenticación y rol de administrador.
    
    - **is_active**: Filtrar por productos activos (default: True)
    
    Retorna: Lista de objetos con {id, name}
    """
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
    
    # Query base
    query = db.query(Product.id, Product.name)
    
    # Filtrar por estado si se especifica
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    # Ordenar alfabéticamente
    query = query.order_by(Product.name.asc())
    
    products = query.all()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Lista de productos obtenida exitosamente",
        "data": {
            "products": [
                {
                    "id": str(p.id),  # Como string para consistencia con descuentos
                    "name": p.name
                }
                for p in products
            ],
            "total": len(products)
        }
    }


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
    product_data: ProductCreate,
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
    existing_product = db.query(Product).filter(Product.slug == product_data.slug).first()
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
    category = db.query(Category).filter(Category.id == product_data.category_id).first()
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
    
    # Crear el producto (validaciones de precio y stock las hace Pydantic)
    new_product = Product(
        name=product_data.name,
        slug=product_data.slug,
        description=product_data.description,
        price=Decimal(str(product_data.price)),
        stock=product_data.stock,
        category_id=product_data.category_id,
        image_url=product_data.image_url,
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
    product_data: ProductUpdate,
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
    if product_data.slug and product_data.slug != product.slug:
        existing_product = db.query(Product).filter(Product.slug == product_data.slug).first()
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
        product.slug = product_data.slug
    
    # Validar categoría si se está actualizando
    if product_data.category_id and product_data.category_id != product.category_id:
        category = db.query(Category).filter(Category.id == product_data.category_id).first()
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
        product.category_id = product_data.category_id
    
    # Actualizar campos opcionales (validaciones las hace Pydantic)
    if product_data.name is not None:
        product.name = product_data.name
    
    if product_data.description is not None:
        product.description = product_data.description
    
    if product_data.price is not None:
        product.price = Decimal(str(product_data.price))
    
    if product_data.stock is not None:
        product.stock = product_data.stock
    
    if product_data.image_url is not None:
        # Solo eliminar la imagen antigua si se está cambiando a una nueva imagen diferente
        if product_data.image_url != product.image_url and product.image_url:
            storage_service.delete_file(product.image_url)
        product.image_url = product_data.image_url
    
    if product_data.is_active is not None:
        product.is_active = product_data.is_active
    
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
    
    Nota: Para eliminar productos permanentemente (hard delete), use el endpoint
    DELETE /products/admin/{product_id}/permanent
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
        "message": "Producto desactivado exitosamente",
        "data": {
            "id": product.id,
            "name": product.name,
            "is_active": product.is_active
        }
    }


@router.delete("/admin/{product_id}/permanent")
async def delete_product_permanent(
    product_id: int,
    force: bool = Query(False, description="Forzar eliminación incluso si tiene órdenes asociadas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar producto permanentemente (hard delete).
    Solo administradores.
    
    ⚠️ PRECAUCIÓN: Esta acción es IRREVERSIBLE.
    
    Por defecto, NO se puede eliminar un producto que tenga órdenes asociadas
    (para mantener el historial de compras).
    
    Use el parámetro ?force=true para forzar la eliminación de productos con órdenes.
    Esto NO eliminará las órdenes, solo desvinculará el producto.
    
    Casos de uso:
    - Limpiar productos de prueba
    - Eliminar productos duplicados
    - Eliminar productos inactivos sin órdenes
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
    
    # Verificar si tiene órdenes asociadas
    from models.order import OrderItem
    orders_count = db.query(OrderItem).filter(OrderItem.product_id == product_id).count()
    
    if orders_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status_code": 400,
                "message": f"No se puede eliminar el producto porque tiene {orders_count} orden(es) asociada(s)",
                "error": "PRODUCT_HAS_ORDERS",
                "data": {
                    "orders_count": orders_count,
                    "suggestion": "Use el parámetro ?force=true para forzar la eliminación"
                }
            }
        )
    
    # Guardar datos antes de eliminar
    product_name = product.name
    product_image = product.image_url
    
    try:
        # Eliminar el producto permanentemente
        db.delete(product)
        db.commit()
        
        # Eliminar la imagen física del disco
        if product_image:
            storage_service.delete_file(product_image)
        
        return {
            "success": True,
            "status_code": 200,
            "message": "Producto eliminado permanentemente",
            "data": {
                "id": product_id,
                "name": product_name,
                "had_orders": orders_count > 0,
                "orders_count": orders_count
            }
        }
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error eliminando producto {product_id}: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "status_code": 500,
                "message": "Error al eliminar producto permanentemente",
                "error": "DATABASE_ERROR",
                "details": str(e)
            }
        )


@router.post("/admin/cleanup-inactive")
async def cleanup_inactive_products(
    days_inactive: int = Query(30, ge=7, description="Días de inactividad mínimos"),
    dry_run: bool = Query(True, description="Solo simular, no eliminar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Limpiar productos inactivos sin órdenes asociadas.
    Solo administradores.
    
    Por defecto ejecuta en modo dry_run (simulación) para ver qué se eliminaría.
    Use ?dry_run=false para ejecutar la limpieza real.
    
    Parámetros:
    - days_inactive: Productos inactivos por al menos N días (default: 30)
    - dry_run: Si es true, solo simula sin eliminar (default: true)
    
    Criterios:
    - Producto está inactivo (is_active = false)
    - No tiene órdenes asociadas
    - Fue desactivado hace más de N días
    """
    from models.order import OrderItem
    from datetime import datetime, timedelta
    
    # Calcular fecha límite
    cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
    
    # Buscar productos inactivos sin órdenes
    inactive_products = db.query(Product).filter(
        Product.is_active == False,
        Product.updated_at < cutoff_date
    ).all()
    
    products_to_delete = []
    products_with_orders = []
    
    for product in inactive_products:
        # Verificar si tiene órdenes
        orders_count = db.query(OrderItem).filter(
            OrderItem.product_id == product.id
        ).count()
        
        if orders_count == 0:
            products_to_delete.append({
                "id": product.id,
                "name": product.name,
                "image_url": product.image_url,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            })
        else:
            products_with_orders.append({
                "id": product.id,
                "name": product.name,
                "orders_count": orders_count
            })
    
    # Si no es dry_run, eliminar productos
    deleted_count = 0
    if not dry_run and products_to_delete:
        for product_data in products_to_delete:
            try:
                product = db.query(Product).filter(Product.id == product_data["id"]).first()
                if product:
                    # Eliminar imagen física
                    if product.image_url:
                        storage_service.delete_file(product.image_url)
                    # Eliminar producto
                    db.delete(product)
                    deleted_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error eliminando producto {product_data['id']}: {str(e)}")
                continue
        
        db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": f"{'Simulación completada' if dry_run else f'Limpieza completada: {deleted_count} productos eliminados'}",
        "data": {
            "dry_run": dry_run,
            "days_inactive": days_inactive,
            "cutoff_date": cutoff_date.isoformat(),
            "products_to_delete": products_to_delete,
            "products_with_orders": products_with_orders,
            "total_deletable": len(products_to_delete),
            "total_with_orders": len(products_with_orders),
            "deleted_count": deleted_count if not dry_run else 0
        }
    }
