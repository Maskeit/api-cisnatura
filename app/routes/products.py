from fastapi import APIRouter, Depends, Query, HTTPException


from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from models.products import Product, Category
from decimal import Decimal
from core.dependencies import get_current_admin_user
from models.user import User
from schemas.products import ProductCreate, ProductUpdate, CategoryCreate, CategoryUpdate

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
    category.is_active = False
    db.commit()
    
    return {
        "success": True,
        "status_code": 200,
        "message": "Categoría eliminada exitosamente",
        "data": {
            "id": category.id,
            "name": category.name,
            "is_active": category.is_active
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
