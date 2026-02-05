#!/bin/bash
# DevOps K8s Platform - Development Setup Script

set -e

echo "🚀 DevOps K8s Platform - Development Setup"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"

# Start infrastructure services
echo "🏗️ Starting infrastructure services..."
docker-compose up -d postgres redis prometheus loki grafana

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U devops -d devops_k8s > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "⚠️ PostgreSQL is not ready yet"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "⚠️ Redis is not ready yet"
fi

echo ""
echo "🎉 Infrastructure services are starting up!"
echo ""
echo "📋 Service URLs:"
echo "   - Grafana: http://localhost:3000 (admin/admin123)"
echo "   - Prometheus: http://localhost:9090"
echo "   - Loki: http://localhost:3100"
echo ""
echo "🔧 Next steps:"
echo "   1. Install backend dependencies: cd backend && pip install -r requirements.txt"
echo "   2. Start backend: cd backend && uvicorn app.main:app --reload"
echo "   3. Start frontend: cd frontend && npm run dev"
echo ""
echo "   Or use the full Docker setup:"
echo "   docker-compose --profile backend --profile frontend up -d"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop services: docker-compose down"