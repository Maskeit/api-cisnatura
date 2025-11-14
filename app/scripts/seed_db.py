"""
Script para poblar la base de datos con datos de ejemplo.
"""
from core.database import SessionLocal
from core.security import hash_password
from models import User, Address, Category, Product, Cart

def seed_data():
    db = SessionLocal()
    
    try:
        print("🌱 Poblando base de datos...")
        
        # Crear categorías de ejemplo
        categories = [
            Category(
                name="Aceites Esenciales",
                slug="aceites-esenciales",
                description="Aceites naturales extraídos de plantas",
                is_active=True
            ),
            Category(
                name="Cuidado de la Piel",
                slug="cuidado-piel",
                description="Productos naturales para el cuidado de la piel",
                is_active=True
            ),
            Category(
                name="Aromaterapia",
                slug="aromaterapia",
                description="Productos para aromaterapia y bienestar",
                is_active=True
            ),
        ]
        
        db.add_all(categories)
        db.commit()
        print("✅ Categorías creadas")
        
        # Crear productos de ejemplo
        products = [
            Product(
                name="Aceite Esencial de Lavanda",
                slug="aceite-lavanda",
                description="Aceite esencial 100% puro de lavanda",
                price=299.99,
                stock=50,
                category_id=1,
                is_active=True
            ),
            Product(
                name="Crema Facial Natural",
                slug="crema-facial",
                description="Crema hidratante con ingredientes naturales",
                price=449.99,
                stock=30,
                category_id=2,
                is_active=True
            ),
            Product(
                name="Difusor de Aromas",
                slug="difusor-aromas",
                description="Difusor eléctrico para aceites esenciales",
                price=799.99,
                stock=20,
                category_id=3,
                is_active=True
            ),
        ]
        
        db.add_all(products)
        db.commit()
        print("✅ Productos creados")
        
        # Crear usuario admin de ejemplo
        admin_user = User(
            email="admin@cisnatura.com",
            hashed_password=hash_password("admin123"),
            full_name="Administrador",
            is_active=True,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)  # Para obtener el UUID generado
        print(f"✅ Usuario admin creado (ID: {admin_user.id}, email: admin@cisnatura.com / admin123)")
        
        # Crear dirección de ejemplo para el admin
        admin_address = Address(
            user_id=admin_user.id,
            label="Casa",
            street="Calle Principal 123",
            city="Ciudad de México",
            state="CDMX",
            postal_code="01000",
            country="México",
            is_default=True
        )
        
        db.add(admin_address)
        db.commit()
        print("✅ Dirección de ejemplo creada")
        
        # Crear carrito para el admin
        admin_cart = Cart(
            user_id=admin_user.id,
            is_active=True
        )
        
        db.add(admin_cart)
        db.commit()
        print("✅ Carrito creado para el usuario admin")
        
        print("\n🎉 Base de datos poblada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
