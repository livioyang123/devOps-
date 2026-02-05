# DevOps K8s Platform - Development Makefile

.PHONY: help install start stop clean test lint format build

# Default target
help:
	@echo "DevOps K8s Platform - Available commands:"
	@echo ""
	@echo "  install     - Install all dependencies"
	@echo "  start       - Start all services"
	@echo "  stop        - Stop all services"
	@echo "  clean       - Clean up containers and volumes"
	@echo "  test        - Run all tests"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo "  build       - Build all containers"
	@echo ""

# Install dependencies
install:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Dependencies installed!"

# Start all services
start:
	@echo "Starting infrastructure services..."
	docker-compose up -d postgres redis prometheus loki grafana
	@echo "Infrastructure services started!"
	@echo ""
	@echo "To start the full stack with containers:"
	@echo "  docker-compose --profile backend --profile frontend up -d"
	@echo ""
	@echo "To start development servers locally:"
	@echo "  Backend: cd backend && uvicorn app.main:app --reload"
	@echo "  Frontend: cd frontend && npm run dev"

# Stop all services
stop:
	@echo "Stopping all services..."
	docker-compose down
	@echo "Services stopped!"

# Clean up
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "Cleanup complete!"

# Run tests
test:
	@echo "Running frontend tests..."
	cd frontend && npm test
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "All tests completed!"

# Run linting
lint:
	@echo "Linting frontend..."
	cd frontend && npm run lint
	@echo "Linting backend..."
	cd backend && black --check . && mypy .
	@echo "Linting completed!"

# Format code
format:
	@echo "Formatting frontend..."
	cd frontend && npm run format
	@echo "Formatting backend..."
	cd backend && black .
	@echo "Code formatting completed!"

# Build containers
build:
	@echo "Building containers..."
	docker-compose build
	@echo "Build completed!"

# Development shortcuts
dev-backend:
	cd backend && uvicorn app.main:app --reload

dev-frontend:
	cd frontend && npm run dev

dev-infra:
	docker-compose up -d postgres redis prometheus loki grafana

# Database operations
db-migrate:
	cd backend && alembic upgrade head

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head

# Monitoring
logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend