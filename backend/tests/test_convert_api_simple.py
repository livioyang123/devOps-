"""
Simple test to verify the conversion API structure without requiring Redis
"""
from app.routers.convert import _reconstruct_compose_yaml
from app.schemas import ComposeStructure, ServiceDefinition, PortMapping


def test_reconstruct_compose_yaml():
    """Test that we can reconstruct YAML from compose structure"""
    compose_structure = ComposeStructure(
        version="3.8",
        services=[
            ServiceDefinition(
                name="web",
                image="nginx:latest",
                ports=[
                    PortMapping(host="8080", container="80", protocol="tcp")
                ],
                environment={"ENV": "production"},
                volumes=["./data:/data"],
                depends_on=["db"]
            ),
            ServiceDefinition(
                name="db",
                image="postgres:13",
                ports=[],
                environment={"POSTGRES_PASSWORD": "secret"},
                volumes=["db-data:/var/lib/postgresql/data"],
                depends_on=[]
            )
        ],
        volumes=[],
        networks=[]
    )
    
    compose_dict = compose_structure.model_dump()
    yaml_content = _reconstruct_compose_yaml(compose_dict)
    
    # Verify the YAML contains expected content
    assert "version: '3.8'" in yaml_content or "version: 3.8" in yaml_content
    assert "web:" in yaml_content
    assert "db:" in yaml_content
    assert "nginx:latest" in yaml_content
    assert "postgres:13" in yaml_content
    assert "8080:80" in yaml_content
    
    print("✓ YAML reconstruction works correctly")
    print("\nReconstructed YAML:")
    print(yaml_content)


def test_api_endpoint_structure():
    """Test that the API endpoints are properly structured"""
    from app.routers import convert
    
    # Verify the router exists
    assert hasattr(convert, 'router')
    
    # Verify the router has the correct prefix
    assert convert.router.prefix == "/api/convert"
    
    # Verify the router has the correct tags
    assert "convert" in convert.router.tags
    
    print("✓ API router structure is correct")


def test_conversion_request_schema():
    """Test that the ConversionRequest schema works correctly"""
    from app.schemas import ConversionRequest, ComposeStructure, ServiceDefinition
    
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
    
    request = ConversionRequest(
        compose_structure=compose_structure,
        model="gpt-4",
        parameters={"temperature": 0.7}
    )
    
    # Verify the request can be serialized
    request_dict = request.model_dump()
    assert request_dict["model"] == "gpt-4"
    assert request_dict["parameters"]["temperature"] == 0.7
    assert len(request_dict["compose_structure"]["services"]) == 1
    
    print("✓ ConversionRequest schema works correctly")


def test_celery_task_exists():
    """Test that the Celery task is properly defined"""
    from app.celery_app import celery_app
    
    # Verify the task is registered
    task_name = 'app.celery_app.convert_compose_to_k8s'
    assert task_name in celery_app.tasks
    
    print(f"✓ Celery task '{task_name}' is registered")


if __name__ == "__main__":
    print("\n=== Testing Conversion API Structure ===\n")
    
    try:
        test_reconstruct_compose_yaml()
        print()
        test_api_endpoint_structure()
        test_conversion_request_schema()
        test_celery_task_exists()
        
        print("\n✓ All structure tests passed!")
        print("\nNote: Full integration tests require Redis and Celery workers to be running.")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
