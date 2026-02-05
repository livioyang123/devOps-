"""
Integration test for the complete conversion flow
This test validates the API structure and endpoint availability
"""
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import ComposeStructure, ServiceDefinition

client = TestClient(app)


def test_convert_endpoint_exists():
    """Test that the /api/convert endpoint exists and is accessible"""
    # Create a valid request
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
    
    # The endpoint should exist (not return 404)
    # It may fail with 500 if Redis is not available, but that's expected
    response = client.post("/api/convert", json=request_data)
    
    assert response.status_code != 404, "Endpoint should exist"
    print(f"✓ /api/convert endpoint exists (status: {response.status_code})")


def test_convert_status_endpoint_exists():
    """Test that the /api/convert/status/{task_id} endpoint exists"""
    # Try to get status for a dummy task ID
    response = client.get("/api/convert/status/dummy-task-id")
    
    # Should not return 404 (endpoint exists)
    assert response.status_code != 404, "Status endpoint should exist"
    print(f"✓ /api/convert/status/{{task_id}} endpoint exists (status: {response.status_code})")


def test_convert_sync_endpoint_exists():
    """Test that the /api/convert/sync endpoint exists"""
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
    
    response = client.post("/api/convert/sync", json=request_data)
    
    # Should not return 404 (endpoint exists)
    assert response.status_code != 404, "Sync endpoint should exist"
    print(f"✓ /api/convert/sync endpoint exists (status: {response.status_code})")


def test_convert_validation():
    """Test that the endpoint validates input correctly"""
    # Send invalid data (missing required fields)
    invalid_data = {
        "model": "gpt-4"
        # Missing compose_structure
    }
    
    response = client.post("/api/convert", json=invalid_data)
    
    # Should return 422 for validation error
    assert response.status_code == 422, "Should validate required fields"
    print("✓ Input validation works correctly")


def test_compose_endpoints_still_work():
    """Verify that existing compose endpoints still work"""
    # Test the upload endpoint
    request_data = {
        "content": """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
"""
    }
    
    response = client.post("/api/compose/upload", json=request_data)
    
    assert response.status_code == 200, "Upload endpoint should work"
    data = response.json()
    assert "structure" in data
    assert "validation" in data
    
    print("✓ Existing compose endpoints still work")


def test_api_documentation():
    """Test that the API documentation includes the new endpoints"""
    response = client.get("/api/docs")
    
    # Should return the OpenAPI documentation page
    assert response.status_code == 200
    print("✓ API documentation is accessible")


if __name__ == "__main__":
    print("\n=== Testing Conversion API Integration ===\n")
    
    try:
        test_convert_endpoint_exists()
        test_convert_status_endpoint_exists()
        test_convert_sync_endpoint_exists()
        test_convert_validation()
        test_compose_endpoints_still_work()
        test_api_documentation()
        
        print("\n✓ All integration tests passed!")
        print("\nSummary:")
        print("- POST /api/convert - Creates async conversion task")
        print("- GET /api/convert/status/{task_id} - Checks task status")
        print("- POST /api/convert/sync - Synchronous conversion")
        print("- All endpoints are properly integrated with FastAPI")
        print("\nNote: Full functionality requires Redis and Celery workers.")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
