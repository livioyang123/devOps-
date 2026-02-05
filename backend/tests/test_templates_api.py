"""
Tests for template management API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime

from app.main import app
from app.database import Base, get_db
from app.models import Template, User
from app.auth import create_access_token

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_templates.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


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
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create authentication token for test user"""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def sample_templates(db_session):
    """Create sample templates for testing"""
    templates = [
        Template(
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
        ),
        Template(
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
        ),
        Template(
            id=uuid.uuid4(),
            name="Private Template",
            description="Private template",
            category="test",
            compose_content="version: '3.8'\nservices: {}",
            required_params=None,
            is_public=False
        )
    ]
    
    for template in templates:
        db_session.add(template)
    
    db_session.commit()
    
    for template in templates:
        db_session.refresh(template)
    
    return templates


class TestListTemplates:
    """Tests for GET /api/templates endpoint"""
    
    def test_list_templates_success(self, sample_templates, auth_headers):
        """Test listing all public templates"""
        response = client.get("/api/templates", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        # Should only return public templates
        assert len(data["templates"]) == 2
        
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
    
    def test_list_templates_no_auth(self, sample_templates):
        """Test listing templates without authentication"""
        response = client.get("/api/templates")
        
        # Should fail without authentication
        assert response.status_code == 401
    
    def test_list_templates_empty(self, auth_headers, db_session):
        """Test listing templates when none exist"""
        response = client.get("/api/templates", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["templates"] == []


class TestGetTemplate:
    """Tests for GET /api/templates/{template_id} endpoint"""
    
    def test_get_template_success(self, sample_templates, auth_headers):
        """Test getting a specific template"""
        template_id = str(sample_templates[0].id)
        response = client.get(f"/api/templates/{template_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == template_id
        assert data["name"] == "WordPress"
        assert data["category"] == "web"
        assert "compose_content" in data
        assert data["required_params"] is not None
    
    def test_get_template_not_found(self, auth_headers):
        """Test getting a non-existent template"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/templates/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_template_invalid_id(self, auth_headers):
        """Test getting a template with invalid ID format"""
        response = client.get("/api/templates/invalid-id", headers=auth_headers)
        
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
    
    def test_get_private_template(self, sample_templates, auth_headers):
        """Test getting a private template (should not be accessible)"""
        private_template = sample_templates[2]
        template_id = str(private_template.id)
        response = client.get(f"/api/templates/{template_id}", headers=auth_headers)
        
        # Private templates should not be accessible
        assert response.status_code == 404


class TestLoadTemplate:
    """Tests for POST /api/templates/{template_id}/load endpoint"""
    
    def test_load_template_without_params(self, sample_templates, auth_headers):
        """Test loading a template that doesn't require parameters"""
        template_id = str(sample_templates[1].id)  # LAMP Stack without params
        response = client.post(
            f"/api/templates/{template_id}/load",
            json={"template_id": template_id},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["template_id"] == template_id
        assert data["name"] == "LAMP Stack"
        assert "compose_content" in data
        assert "message" in data
    
    def test_load_template_with_params(self, sample_templates, auth_headers):
        """Test loading a template with required parameters"""
        template_id = str(sample_templates[0].id)  # WordPress with DB_PASSWORD
        response = client.post(
            f"/api/templates/{template_id}/load",
            json={
                "template_id": template_id,
                "parameters": {
                    "DB_PASSWORD": "secure_password_123"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["template_id"] == template_id
        assert data["name"] == "WordPress"
        # Verify parameter substitution
        assert "{{DB_PASSWORD}}" not in data["compose_content"]
        assert "secure_password_123" in data["compose_content"]
    
    def test_load_template_missing_params(self, sample_templates, auth_headers):
        """Test loading a template without providing required parameters"""
        template_id = str(sample_templates[0].id)  # WordPress requires DB_PASSWORD
        response = client.post(
            f"/api/templates/{template_id}/load",
            json={"template_id": template_id},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "missing required parameters" in response.json()["detail"].lower()
    
    def test_load_template_not_found(self, auth_headers):
        """Test loading a non-existent template"""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/templates/{fake_id}/load",
            json={"template_id": fake_id},
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_load_template_invalid_id(self, auth_headers):
        """Test loading a template with invalid ID format"""
        response = client.post(
            "/api/templates/invalid-id/load",
            json={"template_id": "invalid-id"},
            headers=auth_headers
        )
        
        assert response.status_code == 400


class TestTemplateIntegration:
    """Integration tests for template workflow"""
    
    def test_complete_template_workflow(self, sample_templates, auth_headers):
        """Test complete workflow: list → get → load"""
        # 1. List templates
        list_response = client.get("/api/templates", headers=auth_headers)
        assert list_response.status_code == 200
        templates = list_response.json()["templates"]
        assert len(templates) > 0
        
        # 2. Get specific template
        template_id = templates[0]["id"]
        get_response = client.get(f"/api/templates/{template_id}", headers=auth_headers)
        assert get_response.status_code == 200
        template = get_response.json()
        
        # 3. Load template
        load_payload = {"template_id": template_id}
        
        # Add parameters if required
        if template.get("required_params"):
            params = template["required_params"].get("parameters", [])
            if params:
                load_payload["parameters"] = {param: f"test_{param}" for param in params}
        
        load_response = client.post(
            f"/api/templates/{template_id}/load",
            json=load_payload,
            headers=auth_headers
        )
        assert load_response.status_code == 200
        loaded = load_response.json()
        assert "compose_content" in loaded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
