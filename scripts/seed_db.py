"""
Script para poblar la base de datos con datos de prueba.
Inserta usuarios (cliente y admin) con categorías y productos.
"""

import sys
from pathlib import Path

# Agregar el directorio app al path para importar correctamente
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

from core.database import SessionLocal, Base, engine
from core.security import hash_password
from models import User, Category, Product


def seed_db():
    """Poblar la base de datos con datos de prueba"""
    db = SessionLocal()
    
    try:
        # Crear tablas si no existen
        Base.metadata.create_all(bind=engine)
        
        # Verificar si ya existen datos
        if db.query(User).first():
            print("La base de datos ya contiene datos. Abortando seeding...")
            return
        
        # Crear usuario cliente
        cliente = User(
            email="cliente@example.com",
            hashed_password=hash_password("password123"),
            full_name="Usuario Cliente",
            is_active=True,
            is_admin=False,
            email_verified=True
        )
        
        # Crear usuario admin
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("password123"),
            full_name="Usuario Admin",
            is_active=True,
            is_admin=True,
            email_verified=True
        )
        
        # Crear categoría simple
        categoria = Category(
            name="Categoría de Prueba",
            slug="categoria-de-prueba",
            description="Esta es una categoría de prueba",
            is_active=True
        )
        
        # Agregar categoría para obtener su ID
        db.add(categoria)
        db.flush()  # Flush para obtener el ID sin hacer commit
        
        # Crear producto simple
        producto = Product(
            name="Producto de Prueba",
            slug="producto-de-prueba",
            sku="PROD-001",
            description="Descripción del producto de prueba",
            price=10.00,
            stock=100,
            category_id=categoria.id,
            is_active=True
        )
        
        # Agregar objetos a la base de datos
        db.add(cliente)
        db.add(admin)
        db.add(producto)
        
        # Confirmar los cambios
        db.commit()
        
        print("✓ Base de datos poblada correctamente")
        print(f"  - Usuario cliente: cliente@example.com")
        print(f"  - Usuario admin: admin@example.com")
        print(f"  - Categoría: {categoria.name}")
        print(f"  - Producto: {producto.name}")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error al poblar la base de datos: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()