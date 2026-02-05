# DevOps K8s Platform - Documentation

This directory contains project-level documentation for the DevOps K8s Platform.

## Documentation Structure

### Project Documentation (this folder)
- **README.md** - This file, documentation index
- **FILE_ORGANIZATION.md** - Project file organization guide
- **ORGANIZATION_COMPLETE.md** - Organization completion summary
- **DATABASE_CONNECTION_ERROR.md** - Database connection troubleshooting guide

### Checkpoints (`../checkpoints/`)
- **README.md** - Checkpoints index and overview
- **CHECKPOINT_2_VERIFICATION_RESULTS.md** - Infrastructure verification
- **CHECKPOINT_8_VERIFICATION_RESULTS.md** - Parsing and conversion verification
- **INFRASTRUCTURE_VERIFICATION.md** - Infrastructure setup verification
- **TASK_7_AND_ORGANIZATION_COMPLETE.md** - Task 7 completion summary

### Backend Documentation (`backend/docs/`)
- API implementation guides
- Service documentation
- Task completion summaries
- Quick start guides

### Frontend Documentation (`frontend/docs/`)
- Component documentation
- UI/UX guidelines
- Frontend architecture

### Scripts Documentation (`scripts/`)
- Script usage guides
- Automation documentation

## Quick Links

### Getting Started
1. [Project README](../README.md) - Main project overview
2. [Checkpoints](../checkpoints/README.md) - Verification checkpoints and results
3. [Backend Documentation](../backend/docs/README.md) - Backend API docs

### Development
- [Backend Tests](../backend/tests/README.md) - Running backend tests
- [Frontend Setup](../frontend/README.md) - Frontend development

### Specifications
- [Requirements](../.kiro/specs/devops-k8s-platform/requirements.md)
- [Design](../.kiro/specs/devops-k8s-platform/design.md)
- [Tasks](../.kiro/specs/devops-k8s-platform/tasks.md)

## Documentation Guidelines

### For Test Files
- All test files should be in `backend/tests/` or `frontend/tests/`
- Test files should follow naming convention: `test_*.py` or `*.test.ts`
- Include docstrings explaining what is being tested

### For Documentation Files
- Backend-specific docs go in `backend/docs/`
- Frontend-specific docs go in `frontend/docs/`
- Project-level docs go in `docs/` (this folder)
- Use clear, descriptive filenames
- Include table of contents for long documents

### File Organization
```
project-root/
├── docs/                          # Project-level documentation
│   ├── README.md
│   ├── INFRASTRUCTURE_VERIFICATION.md
│   └── ...
├── backend/
│   ├── docs/                      # Backend-specific documentation
│   │   ├── README.md
│   │   ├── API_GUIDE.md
│   │   └── ...
│   └── tests/                     # Backend tests
│       ├── README.md
│       ├── test_*.py
│       └── ...
├── frontend/
│   ├── docs/                      # Frontend-specific documentation
│   └── tests/                     # Frontend tests
└── scripts/                       # Utility scripts with inline docs
```

## Contributing

When adding new documentation:
1. Place it in the appropriate folder based on scope
2. Update the relevant README.md with a link
3. Use clear, descriptive filenames
4. Include examples where applicable
