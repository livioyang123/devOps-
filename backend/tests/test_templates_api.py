"""
Unit tests for template management API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Template, User
from app.auth import get_password_hash, create_access_token
import uuid

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Create tables and seed test data before each test"""
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    # Create test user
    test_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    db.add(test_user)
    
    # Create test templates
    template1 = Template(
        id=uuid.uuid4(),
        name="WordPress",
        description="WordPress with MySQL database",
        category="web",
        compose_content="""version: '3.8'
services:
  wordpress:
    image: wordpress:latest
    ports:
      - "8080:80"
    environment:
      WORDPRESS_DB_PASSWORD: {{DB_PASSWORD}}
""",
        required_params={
            "parameters": ["DB_PASSWORD"],
            "descriptions": {"DB_PASSWORD": "Database password"}
        },
        is_public=True
    )
    
    template2 = Template(
        id=uuid.uuid4(),
        name="LAMP Stack",
        description="Linux, Apache, MySQL, PHP",
        category="web",
        compose_content="""version: '3.8'
services:
  apache:
    image: php:8.1-apache
    ports:
      - "8080:80"
""",
        required_params=None,
        is_public=True
    )
    
    template3 = Template(
        id=uuid.uuid4(),
        name="Private Template",
        description="Private template",
        category="database",
        compose_content="version: '3.8'\nservices:\n  db:\n    image: postgres:15",
        required_params=None,
        is_public=False
    )
    
    db.add(template1)
    db.add(template2)
    db.add(template3)
    db.commit()
    
    # Store template IDs for tests
    template_ids = {
        "wordpress": str(template1.id),
        "lamp": str(template2.id),
        "private": str(template3.id)
    }
    
    db.close()
    
    yield test_user.id, template_ids
    
    Base.metadata.drop_all(bind=engine)


def get_auth_headers(user_id):
    """Generate authentication headers for testing"""
    access_token = create_access_token(data={"sub": "test@example.com", "user_id": str(user_id)})
    return {"Authorization": f"Bearer {access_token}"}


def test_list_templates(setup_database):
    """Test GET /api/templates endpoint"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    response = client.get("/api/templates", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert len(data["templates"]) == 2  # Only public templates
    
    # Verify template structure
    template = data["templates"][0]
    assert "id" in template
    assert "name" in template
    assert "description" in template
    assert "category" in template
    assert "compose_content" in template
    assert "required_params" in template
    assert "is_public" in template
    assert "created_at" in template


def test_list_templates_unauthorized():
    """Test GET /api/templates without authentication"""
    response = client.get("/api/templates")
    assert response.status_code == 401


def test_get_template_by_id(setup_database):
    """Test GET /api/templates/{template_id} endpoint"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    template_id = template_ids["wordpress"]
    response = client.get(f"/api/templates/{template_id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template_id
    assert data["name"] == "WordPress"
    assert data["category"] == "web"
    assert "{{DB_PASSWORD}}" in data["compose_content"]
    assert data["required_params"] is not None
    assert "DB_PASSWORD" in data["required_params"]["parameters"]


def test_get_template_invalid_id(setup_database):
    """Test GET /api/templates/{template_id} with invalid ID"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    response = client.get("/api/templates/invalid-uuid", headers=headers)
    assert response.status_code == 400
    assert "Invalid template ID format" in response.json()["detail"]


def test_get_template_not_found(setup_database):
    """Test GET /api/templates/{template_id} with non-existent ID"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/templates/{fake_id}", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_private_template(setup_database):
    """Test GET /api/templates/{template_id} for private template"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    template_id = template_ids["private"]
    response = client.get(f"/api/templates/{template_id}", headers=headers)
    assert response.status_code == 404  # Private templates should not be accessible


def test_load_template_without_params(setup_database):
    """Test POST /api/templates/{template_id}/load without parameters"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    template_id = template_ids["lamp"]
    response = client.post(
        f"/api/templates/{template_id}/load",
        headers=headers,
        json={}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == template_id
    assert data["name"] == "LAMP Stack"
    assert "compose_content" in data
    assert "message" in data


def test_load_template_with_params(setup_database):
    """Test POST /api/templates/{template_id}/load with parameters"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    template_id = template_ids["wordpress"]
    response = client.post(
        f"/api/templates/{template_id}/load",
        headers=headers,
        json={
            "parameters": {
                "DB_PASSWORD": "my_secure_password"
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == template_id
    assert data["name"] == "WordPress"
    assert "my_secure_password" in data["compose_content"]
    assert "{{DB_PASSWORD}}" not in data["compose_content"]


def test_load_template_missing_required_params(setup_database):
    """Test POST /api/templates/{template_id}/load with missing required parameters"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    template_id = template_ids["wordpress"]
    response = client.post(
        f"/api/templates/{template_id}/load",
        headers=headers,
        json={}
    )
    
    assert response.status_code == 400
    assert "Missing required parameters" in response.json()["detail"]
    assert "DB_PASSWORD" in response.json()["detail"]


def test_load_template_invalid_id(setup_database):
    """Test POST /api/templates/{template_id}/load with invalid ID"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    response = client.post(
        "/api/templates/invalid-uuid/load",
        headers=headers,
        json={}
    )
    assert response.status_code == 400
    assert "Invalid template ID format" in response.json()["detail"]


def test_load_template_not_found(setup_database):
    """Test POST /api/templates/{template_id}/load with non-existent ID"""
    user_id, template_ids = setup_database
    headers = get_auth_headers(user_id)
    
    fake_id = str(uuid.uuid4())
    response = client.post(
        f"/api/templates/{fake_id}/load",
        headers=headers,
        json={}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
