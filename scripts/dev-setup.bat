@echo off
REM DevOps K8s Platform - Development Setup Script (Windows)

echo 🚀 DevOps K8s Platform - Development Setup
echo ==========================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop and try again.
    exit /b 1
)

echo ✅ Docker is running

REM Start infrastructure services
echo 🏗️ Starting infrastructure services...
docker-compose up -d postgres redis prometheus loki grafana

echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo 🔍 Checking service health...

REM Check PostgreSQL
docker-compose exec -T postgres pg_isready -U devops -d devops_k8s >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL is ready
) else (
    echo ⚠️ PostgreSQL is not ready yet
)

REM Check Redis
docker-compose exec -T redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Redis is ready
) else (
    echo ⚠️ Redis is not ready yet
)

echo.
echo 🎉 Infrastructure services are starting up!
echo.
echo 📋 Service URLs:
echo    - Grafana: http://localhost:3000 (admin/admin123)
echo    - Prometheus: http://localhost:9090
echo    - Loki: http://localhost:3100
echo.
echo 🔧 Next steps:
echo    1. Install backend dependencies: cd backend ^&^& pip install -r requirements.txt
echo    2. Start backend: cd backend ^&^& uvicorn app.main:app --reload
echo    3. Start frontend: cd frontend ^&^& npm run dev
echo.
echo    Or use the full Docker setup:
echo    docker-compose --profile backend --profile frontend up -d
echo.
echo 📊 View logs: docker-compose logs -f
echo 🛑 Stop services: docker-compose down

pause