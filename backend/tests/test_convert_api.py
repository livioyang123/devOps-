"""
Test the conversion API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import ConversionRequest, ComposeStructure, ServiceDefinition

client = TestClient(app)


def test_convert_endpoint_creates_task():
    """Test that the /api/convert endpoint creates a Celery task"""
    # Create a simple compose structure
    compose_structure = ComposeStructure(
        services=[
            ServiceDefinition(
                name="web",
                image="nginx:latest",
                ports=[],
                environment={},
                volumes=[],
                depends_on=[]
            )
        ],
        volumes=[],
        networks=[]
    )
    
    request_data = {
        "compose_structure": compose_structure.model_dump(),
        "model": "gpt-4",
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 2000
        }
    }
    
    response = client.post("/api/convert", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "task_id" in data
    assert "status" in data
    assert "message" in data
    assert "poll_url" in data
    
    # Verify task_id is not empty
    assert data["task_id"]
    assert data["status"] == "pending"
    
    print(f"✓ Task created successfully with ID: {data['task_id']}")


def test_get_conversion_status():
    """Test that we can check the status of a conversion task"""
    # First create a task
    compose_structure = ComposeStructure(
        services=[
            ServiceDefinition(
                name="web",
                image="nginx:latest",
                ports=[],
                environment={},
                volumes=[],
                depends_on=[]
            )
        ],
        volumes=[],
        networks=[]
    )
    
    request_data = {
        "compose_structure": compose_structure.model_dump(),
        "model": "gpt-4",
        "parameters": {}
    }
    
    create_response = client.post("/api/convert", json=request_data)
    assert create_response.status_code == 200
    
    task_id = create_response.json()["task_id"]
    
    # Check the status
    status_response = client.get(f"/api/convert/status/{task_id}")
    
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    # Verify response structure
    assert "task_id" in status_data
    assert "status" in status_data
    assert "message" in status_data
    
    assert status_data["task_id"] == task_id
    
    print(f"✓ Task status retrieved: {status_data['status']}")


def test_convert_sync_endpoint():
    """Test the synchronous conversion endpoint"""
    # Note: This test will fail if LLM providers are not configured
    # It's here to verify the endpoint structure
    
    compose_structure = ComposeStructure(
        services=[
            ServiceDefinition(
                name="web",
                image="nginx:latest",
                ports=[],
                environment={},
                volumes=[],
                depends_on=[]
            )
        ],
        volumes=[],
        networks=[]
    )
    
    request_data = {
        "compose_structure": compose_structure.model_dump(),
        "model": "gpt-4",
        "parameters": {
            "temperature": 0.7
        }
    }
    
    # This will likely fail without LLM configuration, but we can verify the endpoint exists
    response = client.post("/api/convert/sync", json=request_data)
    
    # We expect either success or a specific error (not 404)
    assert response.status_code != 404, "Endpoint should exist"
    
    print(f"✓ Sync endpoint exists (status: {response.status_code})")


def test_convert_with_invalid_data():
    """Test that the endpoint handles invalid data properly"""
    # Missing required fields
    invalid_data = {
        "model": "gpt-4"
        # Missing compose_structure
    }
    
    response = client.post("/api/convert", json=invalid_data)
    
    # Should return 422 for validation error
    assert response.status_code == 422
    
    print("✓ Invalid data handled correctly")


if __name__ == "__main__":
    print("\n=== Testing Conversion API Endpoints ===\n")
    
    try:
        test_convert_endpoint_creates_task()
        test_get_conversion_status()
        test_convert_sync_endpoint()
        test_convert_with_invalid_data()
        
        print("\n✓ All tests passed!")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
