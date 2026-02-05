"""
Tests for configuration API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

from app.main import app
from app.database import Base, get_db
from app.models import User, LLMConfiguration
from app.auth import create_access_token, get_password_hash
from app.encryption import encrypt_api_key, mask_api_key

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_config_api.db"
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


@pytest.fixture
def test_user():
    """Create a test user"""
    db = TestingSessionLocal()
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.close()


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers"""
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


def test_create_llm_config(auth_headers):
    """Test creating LLM configuration"""
    response = client.post(
        "/api/config/llm",
        json={
            "provider": "openai",
            "api_key": "sk-test-key-12345",
            "endpoint": None
        },
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "openai"
    assert "****" in data["api_key_masked"]
    assert data["is_active"] is True


def test_create_llm_config_invalid_provider(auth_headers):
    """Test creating LLM configuration with invalid provider"""
    response = client.post(
        "/api/config/llm",
        json={
            "provider": "invalid_provider",
            "api_key": "sk-test-key-12345"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Invalid provider" in response.json()["detail"]


def test_get_llm_configs(auth_headers, test_user):
    """Test retrieving LLM configurations"""
    # Create a configuration first
    db = TestingSessionLocal()
    encrypted_key = encrypt_api_key("sk-test-key-12345")
    config = LLMConfiguration(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="openai",
        api_key_encrypted=encrypted_key.encode(),
        endpoint=None,
        is_active=True
    )
    db.add(config)
    db.commit()
    db.close()
    
    # Retrieve configurations
    response = client.get("/api/config/llm", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "configurations" in data
    assert len(data["configurations"]) > 0
    assert data["configurations"][0]["provider"] == "openai"
    assert "****" in data["configurations"][0]["api_key_masked"]


def test_get_available_models(auth_headers):
    """Test retrieving available models"""
    response = client.get("/api/config/models", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) > 0
    
    # Check for expected models
    model_ids = [model["id"] for model in data["models"]]
    assert "gpt-4" in model_ids
    assert "claude-sonnet-3.5" in model_ids
    assert "gemini-pro" in model_ids


def test_select_model(auth_headers):
    """Test selecting a model"""
    response = client.post(
        "/api/config/model",
        json={"model": "gpt-4"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gpt-4"
    assert "selected successfully" in data["message"]


def test_select_invalid_model(auth_headers):
    """Test selecting an invalid model"""
    response = client.post(
        "/api/config/model",
        json={"model": "invalid-model"},
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Invalid model" in response.json()["detail"]


def test_update_model_parameters(auth_headers):
    """Test updating model parameters"""
    response = client.post(
        "/api/config/parameters",
        json={
            "parameters": {
                "temperature": 0.8,
                "max_tokens": 2000,
                "system_prompt": "You are a helpful assistant"
            }
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["parameters"]["temperature"] == 0.8
    assert data["parameters"]["max_tokens"] == 2000
    assert data["parameters"]["system_prompt"] == "You are a helpful assistant"


def test_update_model_parameters_invalid_temperature(auth_headers):
    """Test updating model parameters with invalid temperature"""
    response = client.post(
        "/api/config/parameters",
        json={
            "parameters": {
                "temperature": 3.0,  # Invalid: > 2.0
                "max_tokens": 2000
            }
        },
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Temperature must be between" in response.json()["detail"]


def test_update_model_parameters_invalid_max_tokens(auth_headers):
    """Test updating model parameters with invalid max tokens"""
    response = client.post(
        "/api/config/parameters",
        json={
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 50000  # Invalid: > 32000
            }
        },
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Max tokens must be between" in response.json()["detail"]


def test_api_key_masking():
    """Test API key masking functionality"""
    api_key = "sk-1234567890abcdef"
    masked = mask_api_key(api_key)
    
    # Should show last 4 characters
    assert masked.endswith("cdef")
    assert "****" in masked
    assert api_key not in masked


def test_update_existing_llm_config(auth_headers, test_user):
    """Test updating an existing LLM configuration"""
    # Create initial configuration
    response1 = client.post(
        "/api/config/llm",
        json={
            "provider": "openai",
            "api_key": "sk-old-key-12345",
            "endpoint": None
        },
        headers=auth_headers
    )
    assert response1.status_code == 201
    
    # Update the same provider
    response2 = client.post(
        "/api/config/llm",
        json={
            "provider": "openai",
            "api_key": "sk-new-key-67890",
            "endpoint": "https://custom.openai.com"
        },
        headers=auth_headers
    )
    assert response2.status_code == 201
    
    # Verify the configuration was updated
    data = response2.json()
    assert data["provider"] == "openai"
    assert data["endpoint"] == "https://custom.openai.com"
    assert "****" in data["api_key_masked"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
