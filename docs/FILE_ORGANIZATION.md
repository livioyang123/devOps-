# File Organization Guide

## Overview

This document describes the file organization structure for the DevOps K8s Platform project.

## Directory Structure

```
devops-k8s-platform/
├── .kiro/                         # Kiro specifications
│   └── specs/
│       └── devops-k8s-platform/
│           ├── requirements.md
│           ├── design.md
│           └── tasks.md
│
├── docs/                          # Project-level documentation
│   ├── README.md
│   ├── FILE_ORGANIZATION.md       # This file
│   ├── INFRASTRUCTURE_VERIFICATION.md
│   ├── DATABASE_CONNECTION_ERROR.md
│   ├── CHECKPOINT_2_VERIFICATION_RESULTS.md
│   └── TASK_7_AND_ORGANIZATION_COMPLETE.md
│
├── backend/                       # Backend application
│   ├── app/                       # Application code
│   │   ├── routers/              # API endpoints
│   │   ├── services/             # Business logic
│   │   ├── tasks/                # Celery tasks
│   │   ├── models.py             # Database models
│   │   ├── schemas.py            # Pydantic schemas
│   │   └── ...
│   │
│   ├── docs/                      # Backend documentation
│   │   ├── README.md
│   │   ├── CONVERSION_API_IMPLEMENTATION.md
│   │   ├── CONVERTER_SERVICE_IMPLEMENTATION.md
│   │   ├── LLM_ROUTER_IMPLEMENTATION.md
│   │   ├── CACHE_SERVICE_IMPLEMENTATION.md
│   │   ├── AUTHENTICATION_SECURITY_IMPLEMENTATION.md
│   │   ├── TASK_7_COMPLETION_SUMMARY.md
│   │   └── ...
│   │
│   ├── tests/                     # Backend tests
│   │   ├── README.md
│   │   ├── test_*.py             # Test files
│   │   ├── verify_*.py           # Verification scripts
│   │   └── example_*.py          # Example usage scripts
│   │
│   ├── alembic/                   # Database migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   └── ...
│
├── frontend/                      # Frontend application
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   ├── docs/                      # Frontend documentation (to be created)
│   ├── tests/                     # Frontend tests (to be created)
│   └── ...
│
├── infra/                         # Infrastructure configuration
│   ├── grafana/
│   ├── loki/
│   ├── postgres/
│   └── prometheus/
│
├── scripts/                       # Utility scripts
│   ├── dev-setup.bat
│   ├── dev-setup.sh
│   ├── health-check.py
│   └── verify-infrastructure.py
│
├── docker-compose.yml
├── Makefile
└── README.md
```

## File Naming Conventions

### Test Files
- **Backend**: `test_*.py` (e.g., `test_parser_service.py`)
- **Frontend**: `*.test.ts` or `*.test.tsx` (e.g., `Button.test.tsx`)
- **Verification**: `verify_*.py` (e.g., `verify_task_7.py`)
- **Examples**: `example_*.py` (e.g., `example_converter_usage.py`)

### Documentation Files
- Use UPPERCASE with underscores for major docs (e.g., `API_GUIDE.md`)
- Use descriptive names (e.g., `CONVERTER_SERVICE_IMPLEMENTATION.md`)
- Include README.md in each docs folder as an index

### Code Files
- **Python**: snake_case (e.g., `parser_service.py`)
- **TypeScript**: camelCase for files, PascalCase for components (e.g., `Button.tsx`)

## Placement Rules

### Tests
✅ **DO**: Place in `backend/tests/` or `frontend/tests/`
❌ **DON'T**: Place in root or app directories

### Documentation
✅ **DO**: 
- Backend-specific → `backend/docs/`
- Frontend-specific → `frontend/docs/`
- Project-level → `docs/`

❌ **DON'T**: Place in root unless it's the main README.md

### Examples and Utilities
✅ **DO**: Place example scripts in `tests/` folder
✅ **DO**: Place utility scripts in `scripts/` folder
❌ **DON'T**: Mix examples with production code

## Migration Checklist

When organizing existing files:

- [ ] Move all `test_*.py` files to `backend/tests/`
- [ ] Move all `verify_*.py` files to `backend/tests/`
- [ ] Move all `example_*.py` files to `backend/tests/`
- [ ] Move backend documentation to `backend/docs/`
- [ ] Move project documentation to `docs/`
- [ ] Update import paths in moved test files
- [ ] Update documentation links
- [ ] Clean up root directory

## Current Status

✅ **Completed**:
- Created `backend/tests/` directory
- Created `backend/docs/` directory
- Created `docs/` directory
- Moved all test files to appropriate locations
- Moved all documentation files to appropriate locations
- Created README.md files for each directory

## Benefits of This Organization

1. **Clear Separation**: Tests, docs, and code are clearly separated
2. **Easy Navigation**: Developers can quickly find what they need
3. **Scalability**: Structure supports project growth
4. **Best Practices**: Follows Python and TypeScript conventions
5. **CI/CD Friendly**: Test discovery is straightforward
6. **Documentation**: Easy to maintain and update

## Maintenance

- Keep this document updated as the project evolves
- Review file organization during code reviews
- Enforce naming conventions in CI/CD pipelines
- Update README files when adding new sections
