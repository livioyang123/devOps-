# Infrastructure Verification Guide

This guide helps you verify that all infrastructure components of the DevOps K8s Platform are properly set up and running.

## Prerequisites

1. **Docker Desktop** must be installed and running
2. **Python 3.8+** must be installed
3. All required configuration files must be in place

## Quick Start

### Windows

```cmd
# Start Docker Desktop first, then run:
scripts\verify-infrastructure.bat
```

### Linux/Mac

```bash
# Start Docker daemon first, then run:
python3 scripts/verify-infrastructure.py
```

## What Gets Verified

The verification script checks the following components:

### 1. Docker Daemon
- ✅ Verifies Docker is running and accessible

### 2. Docker Compose Services
- ✅ PostgreSQL database
- ✅ Redis cache
- ⚠️  Prometheus (optional)
- ⚠️  Loki (optional)
- ⚠️  Grafana (optional)
- ⚠️  Backend API (optional)
- ⚠️  Celery Worker (optional)
- ⚠️  Frontend (optional)

### 3. PostgreSQL Connection
- ✅ Database is accepting connections
- ✅ Can connect with configured credentials

### 4. Database Migrations
- ✅ Alembic migrations have been applied
- ✅ Database schema is up to date

### 5. Redis Connection
- ✅ Redis is responding to commands
- ✅ SET/GET operations work correctly

### 6. Celery Worker
- ✅ Celery worker container is running
- ✅ Worker is operational and ready

### 7. Service Ports
- ✅ PostgreSQL (5432)
- ✅ Redis (6379)
- ✅ Prometheus (9090)
- ✅ Loki (3100)
- ✅ Grafana (3000)

## Starting Services

### Start Required Services Only

```bash
docker-compose up -d postgres redis
```

### Start All Infrastructure Services

```bash
docker-compose up -d postgres redis prometheus loki grafana
```

### Start Backend Services

```bash
docker-compose --profile backend up -d
```

### Start All Services

```bash
docker-compose --profile backend --profile frontend up -d
```

## Troubleshooting

### Docker Daemon Not Running

**Error:** `Docker daemon is not running`

**Solution:** Start Docker Desktop and wait for it to fully initialize.

### Services Not Starting

**Error:** `Some required services are not running`

**Solution:**
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs postgres
docker-compose logs redis

# Restart services
docker-compose restart postgres redis
```

### PostgreSQL Connection Failed

**Error:** `PostgreSQL is not accessible`

**Solution:**
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify container is healthy
docker inspect devops-postgres | grep -A 5 Health

# Restart PostgreSQL
docker-compose restart postgres
```

### Database Migrations Not Applied

**Error:** `Database migrations not applied`

**Solution:**
```bash
# Option 1: Run migrations from host
cd backend
alembic upgrade head

# Option 2: Run migrations in container
docker-compose exec backend alembic upgrade head
```

### Redis Connection Failed

**Error:** `Redis is not accessible`

**Solution:**
```bash
# Check Redis logs
docker-compose logs redis

# Test Redis manually
docker exec devops-redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### Celery Worker Not Running

**Error:** `Celery worker container is not running`

**Solution:**
```bash
# Start Celery worker
docker-compose --profile backend up -d celery-worker

# Check worker logs
docker-compose logs celery-worker

# Restart worker
docker-compose restart celery-worker
```

### Port Already in Use

**Error:** `Port XXXX is already in use`

**Solution:**
```bash
# Find process using the port (Windows)
netstat -ano | findstr :5432

# Kill the process (Windows - replace PID)
taskkill /PID <PID> /F

# Or change the port in docker-compose.yml
```

## Manual Verification Steps

If the automated script fails, you can manually verify each component:

### 1. Check Docker

```bash
docker info
docker-compose ps
```

### 2. Check PostgreSQL

```bash
docker exec devops-postgres pg_isready -U devops -d devops_k8s
docker exec devops-postgres psql -U devops -d devops_k8s -c "SELECT version();"
```

### 3. Check Redis

```bash
docker exec devops-redis redis-cli ping
docker exec devops-redis redis-cli SET test_key test_value
docker exec devops-redis redis-cli GET test_key
```

### 4. Check Database Schema

```bash
docker exec devops-postgres psql -U devops -d devops_k8s -c "\dt"
docker exec devops-postgres psql -U devops -d devops_k8s -c "SELECT * FROM alembic_version;"
```

### 5. Check Celery Worker

```bash
docker logs devops-celery-worker --tail 50
docker exec devops-celery-worker celery -A app.celery_app inspect active
```

## Expected Output

When all checks pass, you should see:

```
============================================================
  Verification Summary
============================================================
✅ PASS      Docker Daemon
✅ PASS      Docker Compose Services
✅ PASS      PostgreSQL Connection
✅ PASS      Database Migrations
✅ PASS      Redis Connection
✅ PASS      Celery Worker
✅ PASS      Service Ports

============================================================
Result: 7/7 checks passed
============================================================

🎉 All infrastructure checks passed!
Your DevOps K8s Platform infrastructure is ready.
```

## Next Steps

Once all infrastructure checks pass:

1. ✅ Infrastructure is verified and ready
2. 🚀 You can proceed with implementing backend services
3. 📝 Continue with task 3 in the implementation plan

## Getting Help

If you encounter issues not covered in this guide:

1. Check Docker Desktop logs
2. Review docker-compose.yml configuration
3. Verify environment variables in backend/.env
4. Check service logs: `docker-compose logs <service-name>`
5. Ensure all required ports are available
