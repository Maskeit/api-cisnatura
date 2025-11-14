"""
Script para inicializar la base de datos.
Crea todas las tablas definidas en models/
"""
from core.database import engine, Base
from models import User, Address, Category, Product, Cart, Order, OrderItem, CartItem

def init_db():
    """Crear todas las tablas en la base de datos"""
    print("🔨 Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente!")

def drop_db():
    """Eliminar todas las tablas de la base de datos"""
    print("⚠️  Eliminando todas las tablas...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tablas eliminadas!")

if __name__ == "__main__":
    init_db()
