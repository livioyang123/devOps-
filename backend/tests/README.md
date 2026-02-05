# Backend Tests

This directory contains all test files and verification scripts for the DevOps K8s Platform backend.

## Test Organization

### Unit Tests
- **test_parser_service.py** - Parser service unit tests
- **test_converter_service.py** - Converter service unit tests
- **test_llm_router.py** - LLM router unit tests
- **test_cache_service.py** - Cache service unit tests
- **test_auth_security.py** - Authentication and security tests
- **test_models.py** - Database models tests

### API Tests
- **test_compose_api.py** - Compose endpoints tests
- **test_convert_api.py** - Conversion endpoints tests (requires Redis)
- **test_convert_api_simple.py** - Conversion API structure tests (no Redis)
- **test_convert_integration.py** - Conversion API integration tests

### Integration Tests
- **test_converter_integration.py** - Full converter integration tests
- **test_db_connection.py** - Database connection tests
- **test_redis_celery.py** - Redis and Celery integration tests

### Celery Tests
- **test_celery_config.py** - Celery configuration tests
- **test_simple_task.py** - Simple Celery task tests
- **test_task_direct.py** - Direct task execution tests
- **test_final_task.py** - Final task tests
- **minimal_celery_test.py** - Minimal Celery setup test
- **simple_celery_test.py** - Simple Celery test

### Manual Tests
- **test_parser_manual.py** - Manual parser testing
- **test_direct_call.py** - Direct function call tests

### Verification Scripts
- **verify_converter_implementation.py** - Verify converter implementation
- **verify_task_7.py** - Verify Task 7 completion

### Example Scripts
- **example_converter_usage.py** - Example of using the converter service
- **example_converter_integration.py** - Example of converter integration
- **example_llm_usage.py** - Example of using LLM router

## Running Tests

**Important:** All tests must be run from the `/backend` directory, not from `/backend/tests`.

```bash
cd backend  # Make sure you're in the backend directory
```

### All Tests
```bash
pytest tests/
```

### Specific Test Categories

#### Unit Tests (No external dependencies)
```bash
pytest tests/test_parser_service.py
pytest tests/test_converter_service.py
pytest tests/test_llm_router.py
```

#### API Tests (Requires running server)
```bash
python -m tests.test_convert_api_simple
python -m tests.test_convert_integration
```

#### Integration Tests (Requires Redis & Celery)
```bash
# Start Redis and Celery first
docker-compose up redis
celery -A app.celery_app worker --loglevel=info

# Then run tests
pytest tests/test_convert_api.py
pytest tests/test_redis_celery.py
```

### Verification Scripts
```bash
# Verify Task 7 implementation
python -m tests.verify_task_7

# Verify converter implementation
python -m tests.verify_converter_implementation
```

### Example Scripts
```bash
# Run examples to see how to use the services
python -m tests.example_converter_usage
python -m tests.example_llm_usage
```

## Test Requirements

### Minimal (No external services)
- Python 3.11+
- pytest
- FastAPI TestClient

### Full Integration
- Redis running (docker-compose up redis)
- Celery worker running
- PostgreSQL running (for database tests)
- LLM API keys configured (for converter tests)

## Test Coverage

Run with coverage:
```bash
pytest tests/ --cov=app --cov-report=html
```

View coverage report:
```bash
# Open htmlcov/index.html in browser
```

## Writing New Tests

### Unit Test Template
```python
"""
Test module description
"""
import pytest
from app.services.your_service import YourService


def test_your_function():
    """Test description"""
    service = YourService()
    result = service.your_function()
    assert result == expected_value
```

### API Test Template
```python
"""
API test description
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_your_endpoint():
    """Test description"""
    response = client.post("/api/your-endpoint", json={...})
    assert response.status_code == 200
```

## Continuous Integration

Tests are run automatically on:
- Every commit (unit tests)
- Pull requests (unit + integration tests)
- Nightly builds (full test suite with extended iterations)

## Related Documentation
- `/backend/docs/` - Implementation documentation
- `/.kiro/specs/devops-k8s-platform/` - Requirements and design
- `/backend/app/` - Source code being tested
