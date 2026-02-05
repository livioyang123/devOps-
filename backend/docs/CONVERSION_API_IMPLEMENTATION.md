# Conversion API Implementation

## Overview

This document describes the implementation of the Docker Compose to Kubernetes conversion API endpoints (Task 7.2).

## Implemented Components

### 1. API Endpoints

#### POST /api/convert
Creates an asynchronous Celery task for converting Docker Compose to Kubernetes manifests.

**Request Body:**
```json
{
  "compose_structure": {
    "services": [...],
    "volumes": [...],
    "networks": [...]
  },
  "model": "gpt-4",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

**Response:**
```json
{
  "task_id": "abc123...",
  "status": "pending",
  "message": "Conversion task created successfully",
  "poll_url": "/api/convert/status/abc123..."
}
```

#### GET /api/convert/status/{task_id}
Retrieves the status and result of a conversion task.

**Response (Pending):**
```json
{
  "task_id": "abc123...",
  "status": "PENDING",
  "message": "Task is waiting to be processed"
}
```

**Response (Success):**
```json
{
  "task_id": "abc123...",
  "status": "SUCCESS",
  "message": "Task completed successfully",
  "result": {
    "manifests": [...],
    "cached": false,
    "conversion_time": 2.5,
    "model_used": "gpt-4",
    "status": "completed"
  }
}
```

#### POST /api/convert/sync
Performs synchronous conversion (for testing or immediate results).

**Request/Response:** Same as async endpoint, but returns manifests directly.

### 2. Celery Task

The `convert_compose_to_k8s` task in `app/celery_app.py` performs the actual conversion:

1. Validates input parameters
2. Parses Docker Compose content using ParserService
3. Converts to Kubernetes manifests using ConverterService
4. Leverages CacheService for response caching
5. Returns manifests with metadata

**Task Signature:**
```python
@celery_app.task
def convert_compose_to_k8s(
    compose_content: str,
    model: str,
    parameters: dict
) -> dict
```

### 3. Helper Functions

#### _reconstruct_compose_yaml()
Reconstructs Docker Compose YAML from parsed structure. This is necessary because:
- The API receives a parsed ComposeStructure object
- The ConverterService needs the original YAML content
- The function rebuilds valid Docker Compose YAML from the structure

## Integration Points

### Services Used
- **ParserService**: Validates and parses Docker Compose content
- **ConverterService**: Converts Docker Compose to Kubernetes using LLM
- **LLMRouter**: Routes requests to appropriate LLM provider
- **CacheService**: Caches conversion results to reduce API costs

### Data Flow
```
Client Request
    ↓
POST /api/convert
    ↓
Create Celery Task
    ↓
Return Task ID
    ↓
[Async Processing]
    ↓
ParserService.parse_compose()
    ↓
ConverterService.convert_to_k8s()
    ↓
LLMRouter.generate()
    ↓
CacheService.cache_conversion()
    ↓
Store Result in Redis
    ↓
Client Polls Status
    ↓
GET /api/convert/status/{task_id}
    ↓
Return Result
```

## Requirements Satisfied

### Requirement 3.1: AI-Powered Kubernetes Conversion
✓ Implemented through ConverterService integration

### Requirement 20.1: Asynchronous Task Creation
✓ POST /api/convert creates Celery task and returns task ID

### Requirement 20.2: Task ID for Status Polling
✓ Task ID returned in response with poll_url

## Testing

### Structure Tests
Run `python backend/test_convert_api_simple.py` to verify:
- YAML reconstruction works correctly
- API router structure is correct
- ConversionRequest schema works
- Celery task is registered

### Integration Tests
Run `python backend/test_convert_integration.py` to verify:
- All endpoints exist and are accessible
- Input validation works correctly
- Existing compose endpoints still work
- API documentation includes new endpoints

### Full Integration Tests (Requires Redis)
Run `python -m pytest backend/test_convert_api.py` to test:
- Task creation and status polling
- Complete async workflow
- Error handling

## Configuration

### Environment Variables
The following environment variables must be set (in `.env`):
- `CELERY_BROKER_URL`: Redis URL for Celery broker
- `CELERY_RESULT_BACKEND`: Redis URL for result storage
- LLM provider API keys (OPENAI_API_KEY, etc.)

### Dependencies
- FastAPI for API endpoints
- Celery for async task processing
- Redis for task queue and result storage
- PyYAML for YAML processing

## Usage Example

### Python Client
```python
import requests

# 1. Create conversion task
response = requests.post("http://localhost:8000/api/convert", json={
    "compose_structure": {
        "services": [
            {
                "name": "web",
                "image": "nginx:latest",
                "ports": [],
                "environment": {},
                "volumes": [],
                "depends_on": []
            }
        ],
        "volumes": [],
        "networks": []
    },
    "model": "gpt-4",
    "parameters": {"temperature": 0.7}
})

task_id = response.json()["task_id"]

# 2. Poll for status
import time
while True:
    status_response = requests.get(
        f"http://localhost:8000/api/convert/status/{task_id}"
    )
    status = status_response.json()
    
    if status["status"] == "SUCCESS":
        manifests = status["result"]["manifests"]
        break
    elif status["status"] == "FAILURE":
        print("Conversion failed:", status["error"])
        break
    
    time.sleep(1)
```

### cURL
```bash
# Create task
curl -X POST http://localhost:8000/api/convert \
  -H "Content-Type: application/json" \
  -d '{
    "compose_structure": {...},
    "model": "gpt-4",
    "parameters": {}
  }'

# Check status
curl http://localhost:8000/api/convert/status/{task_id}
```

## Error Handling

### Validation Errors (422)
- Missing required fields
- Invalid data types
- Malformed compose structure

### Server Errors (500)
- Redis connection failure
- Celery worker unavailable
- LLM provider errors
- Parsing errors

### Task Failures
- Stored in task result with error details
- Accessible via status endpoint
- Includes error message and stack trace

## Future Enhancements

1. **WebSocket Support**: Real-time progress updates during conversion
2. **Batch Conversion**: Convert multiple compose files in parallel
3. **Conversion History**: Store and retrieve past conversions
4. **Custom Templates**: Allow users to define conversion templates
5. **Validation**: Pre-validate compose files before conversion

## Related Files

- `backend/app/routers/convert.py` - API endpoints
- `backend/app/celery_app.py` - Celery task definition
- `backend/app/tasks/conversion.py` - Task implementation (reference)
- `backend/app/services/converter.py` - Conversion logic
- `backend/app/services/parser.py` - Compose parsing
- `backend/app/schemas.py` - Request/response models

## Maintenance Notes

- The Celery task is defined in `celery_app.py` for simplicity
- The `_reconstruct_compose_yaml()` function is a workaround; ideally, preserve original YAML
- Error handling includes retry logic in ConverterService
- Cache TTL is 24 hours (configurable in CacheService)
