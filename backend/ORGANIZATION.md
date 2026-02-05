# Backend Organization

## Directory Structure

```
backend/
├── app/                    # Application source code
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic services
│   ├── tasks/             # Celery tasks
│   ├── models.py          # Database models
│   ├── schemas.py         # Pydantic schemas
│   ├── auth.py            # Authentication
│   ├── middleware.py      # Middleware
│   ├── encryption.py      # Encryption utilities
│   ├── config.py          # Configuration
│   ├── database.py        # Database connection
│   ├── redis_client.py    # Redis connection
│   ├── celery_app.py      # Celery configuration
│   └── main.py            # FastAPI application
│
├── docs/                   # Documentation
│   ├── README.md          # Documentation index
│   ├── AUTHENTICATION_SECURITY_IMPLEMENTATION.md
│   ├── CACHE_SERVICE_IMPLEMENTATION.md
│   ├── CONVERSION_API_IMPLEMENTATION.md
│   ├── CONVERTER_IMPLEMENTATION_SUMMARY.md
│   ├── CONVERTER_QUICK_START.md
│   ├── CONVERTER_SERVICE_IMPLEMENTATION.md
│   ├── LLM_ROUTER_IMPLEMENTATION.md
│   └── TASK_7_COMPLETION_SUMMARY.md
│
├── tests/                  # Test files
│   ├── README.md          # Test documentation
│   ├── __init__.py        # Test package init
│   │
│   ├── test_*.py          # Unit and integration tests
│   ├── verify_*.py        # Verification scripts
│   ├── example_*.py       # Example usage scripts
│   └── *_test.py          # Additional test files
│
├── alembic/               # Database migrations
│   ├── versions/          # Migration versions
│   └── env.py             # Alembic environment
│
├── .env                   # Environment variables (not in git)
├── .env.example           # Environment template
├── alembic.ini            # Alembic configuration
├── celery_worker.py       # Celery worker entry point
├── Dockerfile             # Docker image definition
├── pyproject.toml         # Python project configuration
├── requirements.txt       # Python dependencies
└── run_migrations.py      # Migration runner script
```

## Key Directories

### `/app` - Application Code
Contains all production application code:
- **routers/** - FastAPI route handlers (API endpoints)
- **services/** - Business logic and external service integrations
- **tasks/** - Celery background tasks
- Core modules: models, schemas, auth, middleware, config

### `/docs` - Documentation
All implementation documentation and guides:
- Service implementation details
- API endpoint documentation
- Quick start guides
- Task completion summaries

See `/backend/docs/README.md` for complete documentation index.

### `/tests` - Tests
All test files, verification scripts, and examples:
- Unit tests for services and utilities
- Integration tests for API endpoints
- Celery task tests
- Verification scripts
- Usage examples

See `/backend/tests/README.md` for testing guide.

## Running the Application

### Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Celery Worker
```bash
celery -A app.celery_app worker --loglevel=info
```

### With Docker Compose
```bash
docker-compose up
```

## Running Tests

### All Tests
```bash
pytest tests/
```

### Specific Test File
```bash
pytest tests/test_parser_service.py
```

### With Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Verification Scripts
```bash
python tests/verify_task_7.py
```

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:
- Database connection (PostgreSQL)
- Redis connection
- Celery broker and backend
- LLM provider API keys
- JWT secret key
- Encryption key

### Database Migrations
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## API Documentation

Once the server is running, access:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Development Workflow

1. **Write Code** in `/app`
2. **Write Tests** in `/tests`
3. **Document** in `/docs`
4. **Run Tests** with pytest
5. **Verify** with verification scripts
6. **Commit** changes

## Code Quality

### Linting
```bash
black app/ tests/
mypy app/
```

### Type Checking
```bash
mypy app/
```

### Testing
```bash
pytest tests/ --cov=app
```

## Related Documentation

- **Project Specs**: `/.kiro/specs/devops-k8s-platform/`
  - requirements.md - Feature requirements
  - design.md - System design
  - tasks.md - Implementation tasks

- **Backend Docs**: `/backend/docs/`
  - Implementation details
  - API documentation
  - Service guides

- **Tests**: `/backend/tests/`
  - Test documentation
  - Example scripts
  - Verification tools

## Notes

- All test files follow pytest conventions (`test_*.py`)
- Documentation uses Markdown format
- Code follows Black formatting and mypy type checking
- API follows OpenAPI/Swagger standards
- Database uses Alembic for migrations
