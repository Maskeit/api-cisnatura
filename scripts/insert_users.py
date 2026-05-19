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
from models import User
def seed_db():
    """Poblar la base de datos con datos de prueba"""
    db = SessionLocal()
    
    try:
        # Crear tablas si no existen
        Base.metadata.create_all(bind=engine)
        
        
        # Crear usuario cliente
        cliente1 = User(
            email="cliente1@example.com",
            hashed_password=hash_password("password123"),
            full_name="Usuario Cliente",
            is_active=True,
            is_admin=False,
            email_verified=True
        )

        cliente2 = User(
            email="cliente2@example.com",
            hashed_password=hash_password("password123"),
            full_name="Usuario Cliente",
            is_active=True,
            is_admin=False,
            email_verified=True
        )
        
        db.add(cliente1)
        db.add(cliente2)
        
        # Confirmar los cambios
        db.commit()
        
        print("✓ Base de datos poblada correctamente")
        print(f"  - Usuario cliente: cliente1@example.com")
        print(f"  - Usuario cliente: cliente2@example.com")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error al poblar la base de datos: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()