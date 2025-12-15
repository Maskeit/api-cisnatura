"""
Tests de seguridad para validar autorizaciones y permisos en rutas.
Ejecutar con: pytest tests/test_security.py -v
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import sys
import os

# Agregar app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import app
from core.database import get_db, SessionLocal
from models.user import User
from core.security import hash_password
from sqlalchemy import text
import uuid


@pytest.fixture
def test_db():
    """Fixture para base de datos de prueba"""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def client():
    """Fixture para cliente HTTP"""
    return TestClient(app)


@pytest.fixture
def admin_token(client, test_db):
    """Crear admin de prueba y retornar token"""
    # Limpiar usuario anterior si existe
    test_db.query(User).filter(User.email == "admin@test.com").delete()
    test_db.commit()
    
    # Crear admin
    admin = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=hash_password("Admin123"),
        full_name="Admin Test",
        is_admin=True,
        email_verified=True,
        is_active=True
    )
    test_db.add(admin)
    test_db.commit()
    
    # Login y obtener token
    response = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "Admin123"}
    )
    
    return response.json()["data"]["access_token"]


@pytest.fixture
def user_token(client, test_db):
    """Crear usuario normal de prueba y retornar token"""
    # Limpiar usuario anterior si existe
    test_db.query(User).filter(User.email == "user@test.com").delete()
    test_db.commit()
    
    # Crear usuario normal
    user = User(
        id=uuid.uuid4(),
        email="user@test.com",
        hashed_password=hash_password("User123"),
        full_name="User Test",
        is_admin=False,
        email_verified=True,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    
    # Login y obtener token
    response = client.post(
        "/auth/login",
        json={"email": "user@test.com", "password": "User123"}
    )
    
    return response.json()["data"]["access_token"]


# ==================== TESTS DE AUTORIZACIÓN ====================

class TestAuthorizationSecurity:
    """Tests para validar autorización en rutas protegidas"""
    
    def test_ruta_publica_sin_autenticacion(self, client):
        """Las rutas públicas deben ser accesibles sin token"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_health_check_sin_autenticacion(self, client):
        """Health check debe ser accesible sin token"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_ruta_protegida_sin_token(self, client):
        """Rutas protegidas deben retornar 401 sin token"""
        response = client.get("/users/me")
        assert response.status_code == 403 or response.status_code == 401
    
    def test_ruta_protegida_con_token_invalido(self, client):
        """Token inválido debe ser rechazado"""
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code in [401, 403]
    
    def test_admin_endpoint_con_usuario_normal(self, client, user_token):
        """Usuario normal no puede acceder a endpoints de admin"""
        response = client.get(
            "/users/admin/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [403, 401]
    
    def test_admin_endpoint_con_admin(self, client, admin_token):
        """Admin puede acceder a endpoints de admin"""
        response = client.get(
            "/users/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Puede retornar 200 o error de otro tipo, pero NO 403
        assert response.status_code != 403


class TestProductManagement:
    """Tests de seguridad en gestión de productos"""
    
    def test_crear_producto_sin_autenticacion(self, client):
        """No autenticado no puede crear productos"""
        response = client.post(
            "/products/",
            json={
                "name": "Test",
                "slug": "test",
                "description": "Test product",
                "price": 100,
                "stock": 10,
                "category_id": 1
            }
        )
        assert response.status_code in [401, 403]
    
    def test_crear_producto_usuario_normal(self, client, user_token):
        """Usuario normal no puede crear productos"""
        response = client.post(
            "/products/",
            json={
                "name": "Test",
                "slug": "test",
                "description": "Test product",
                "price": 100,
                "stock": 10,
                "category_id": 1
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [401, 403]
    
    def test_eliminar_producto_usuario_normal(self, client, user_token):
        """Usuario normal no puede eliminar productos"""
        response = client.delete(
            "/products/1",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [401, 403]


class TestUploadSecurity:
    """Tests de seguridad en uploads de archivos"""
    
    def test_upload_sin_autenticacion(self, client):
        """No autenticado no puede subir archivos"""
        response = client.post("/uploads/products")
        assert response.status_code in [401, 403, 422]


class TestSQLInjection:
    """Tests para detectar vulnerabilidades de SQL injection"""
    
    def test_search_con_sql_injection(self, client):
        """Búsqueda debe estar protegida contra SQL injection"""
        # Intentar SQL injection en búsqueda
        response = client.get(
            "/products/?search='; DROP TABLE products; --"
        )
        # No debe causar error de BD, debe retornar 200 (sin resultados)
        assert response.status_code == 200
        assert "DROP TABLE" not in response.text
    
    def test_filter_con_sql_injection(self, client):
        """Filtros deben estar protegidos contra SQL injection"""
        response = client.get(
            "/products/?category_id=1 OR 1=1"
        )
        # Debe retornar 200 sin problemas
        assert response.status_code == 200


# ==================== INSTRUCCIONES DE USO ====================
"""
Para ejecutar estos tests:

1. Instalar dependencias de desarrollo:
   pip install -r requirements-dev.txt

2. Ejecutar todos los tests:
   pytest tests/test_security.py -v

3. Ejecutar un test específico:
   pytest tests/test_security.py::TestAuthorizationSecurity::test_admin_endpoint_con_usuario_normal -v

4. Con reporte HTML:
   pytest tests/test_security.py -v --html=report.html --self-contained-html

5. Con coverage:
   pytest tests/test_security.py --cov=app --cov-report=html

Resultados esperados:
- ✅ Todas las autorizaciones funcionan correctamente
- ✅ SQL injection está protegido
- ✅ Rutas públicas son accesibles
- ✅ Rutas protegidas requieren autenticación
"""
