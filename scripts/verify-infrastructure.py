#!/usr/bin/env python3
"""
Infrastructure Verification Script for DevOps K8s Platform
Verifies that all Docker services are running, database migrations are applied,
Redis is accessible, and Celery workers are operational.
"""

import os
import sys
import time
import subprocess
import socket
from typing import Tuple, List

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")

def print_section(text: str):
    """Print a section header"""
    print(f"\n🔍 {text}")
    print("-" * 60)

def run_command(command: List[str], capture_output: bool = True) -> Tuple[bool, str]:
    """Run a shell command and return success status and output"""
    try:
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def check_docker_running() -> bool:
    """Check if Docker daemon is running"""
    print_section("Checking Docker Daemon")
    success, output = run_command(["docker", "info"])
    if success:
        print("✅ Docker daemon is running")
        return True
    else:
        print("❌ Docker daemon is not running")
        print("   Please start Docker Desktop and try again")
        return False

def check_docker_compose_services() -> bool:
    """Check if Docker Compose services are running"""
    print_section("Checking Docker Compose Services")
    
    # Check if services are running
    success, output = run_command(["docker-compose", "ps", "--services", "--filter", "status=running"])
    
    if not success:
        print("❌ Failed to check Docker Compose services")
        print("   Run: docker-compose up -d")
        return False
    
    running_services = [s.strip() for s in output.strip().split('\n') if s.strip()]
    
    required_services = ["postgres", "redis"]
    optional_services = ["prometheus", "loki", "grafana", "backend", "celery-worker", "frontend"]
    
    all_good = True
    
    print("\nRequired Services:")
    for service in required_services:
        if service in running_services:
            print(f"  ✅ {service}")
        else:
            print(f"  ❌ {service} (not running)")
            all_good = False
    
    print("\nOptional Services:")
    for service in optional_services:
        if service in running_services:
            print(f"  ✅ {service}")
        else:
            print(f"  ⚠️  {service} (not running - optional)")
    
    if not all_good:
        print("\n❌ Some required services are not running")
        print("   Run: docker-compose up -d postgres redis")
        return False
    
    print("\n✅ All required Docker Compose services are running")
    return True

def check_postgres_connection() -> bool:
    """Check if PostgreSQL is accessible"""
    print_section("Checking PostgreSQL Connection")
    
    # Try to connect using docker exec
    success, output = run_command([
        "docker", "exec", "devops-postgres",
        "pg_isready", "-U", "devops", "-d", "devops_k8s"
    ])
    
    if success and "accepting connections" in output:
        print("✅ PostgreSQL is accepting connections")
        return True
    else:
        print("❌ PostgreSQL is not accessible")
        print(f"   Output: {output}")
        return False

def check_database_migrations() -> bool:
    """Check if database migrations have been applied"""
    print_section("Checking Database Migrations")
    
    # Check if alembic_version table exists
    success, output = run_command([
        "docker", "exec", "devops-postgres",
        "psql", "-U", "devops", "-d", "devops_k8s",
        "-c", "SELECT version_num FROM alembic_version;"
    ])
    
    if success and "version_num" in output:
        # Extract version from output
        lines = output.strip().split('\n')
        if len(lines) >= 3:
            version = lines[2].strip()
            print(f"✅ Database migrations applied (current version: {version})")
            return True
        else:
            print("⚠️  Alembic version table exists but no version found")
            print("   You may need to run migrations")
            return False
    else:
        print("❌ Database migrations not applied")
        print("   Run: docker-compose exec backend alembic upgrade head")
        print("   Or: cd backend && alembic upgrade head")
        return False

def check_redis_connection() -> bool:
    """Check if Redis is accessible"""
    print_section("Checking Redis Connection")
    
    success, output = run_command([
        "docker", "exec", "devops-redis",
        "redis-cli", "ping"
    ])
    
    if success and "PONG" in output:
        print("✅ Redis is responding to PING")
        
        # Test set/get
        success, _ = run_command([
            "docker", "exec", "devops-redis",
            "redis-cli", "SET", "test_key", "test_value"
        ])
        
        if success:
            success, output = run_command([
                "docker", "exec", "devops-redis",
                "redis-cli", "GET", "test_key"
            ])
            
            if success and "test_value" in output:
                print("✅ Redis SET/GET operations working")
                
                # Clean up
                run_command([
                    "docker", "exec", "devops-redis",
                    "redis-cli", "DEL", "test_key"
                ])
                return True
        
        print("⚠️  Redis PING works but SET/GET failed")
        return False
    else:
        print("❌ Redis is not accessible")
        return False

def check_celery_worker() -> bool:
    """Check if Celery worker is running"""
    print_section("Checking Celery Worker")
    
    # Check if celery-worker container is running
    success, output = run_command([
        "docker", "ps", "--filter", "name=devops-celery-worker",
        "--filter", "status=running", "--format", "{{.Names}}"
    ])
    
    if success and "devops-celery-worker" in output:
        print("✅ Celery worker container is running")
        
        # Check worker logs for successful startup
        success, output = run_command([
            "docker", "logs", "--tail", "50", "devops-celery-worker"
        ])
        
        if success:
            if "ready" in output.lower() or "celery@" in output.lower():
                print("✅ Celery worker appears to be operational")
                return True
            else:
                print("⚠️  Celery worker container running but may not be ready")
                print("   Check logs: docker logs devops-celery-worker")
                return False
        else:
            print("⚠️  Could not check Celery worker logs")
            return False
    else:
        print("❌ Celery worker container is not running")
        print("   Run: docker-compose --profile backend up -d celery-worker")
        return False

def check_port_accessibility(port: int, service: str) -> bool:
    """Check if a port is accessible on localhost"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print(f"  ✅ {service} port {port} is accessible")
            return True
        else:
            print(f"  ❌ {service} port {port} is not accessible")
            return False
    except Exception as e:
        print(f"  ❌ {service} port {port} check failed: {e}")
        return False

def check_service_ports() -> bool:
    """Check if service ports are accessible"""
    print_section("Checking Service Ports")
    
    ports = [
        (5432, "PostgreSQL"),
        (6379, "Redis"),
        (9090, "Prometheus"),
        (3100, "Loki"),
        (3000, "Grafana"),
    ]
    
    all_good = True
    for port, service in ports:
        if not check_port_accessibility(port, service):
            all_good = False
    
    return all_good

def main():
    """Main verification function"""
    print_header("DevOps K8s Platform - Infrastructure Verification")
    
    checks = []
    
    # 1. Check Docker daemon
    docker_ok = check_docker_running()
    checks.append(("Docker Daemon", docker_ok))
    
    if not docker_ok:
        print_header("❌ VERIFICATION FAILED")
        print("Docker daemon is not running. Please start Docker Desktop.")
        return 1
    
    # 2. Check Docker Compose services
    services_ok = check_docker_compose_services()
    checks.append(("Docker Compose Services", services_ok))
    
    if not services_ok:
        print_header("❌ VERIFICATION FAILED")
        print("Required Docker services are not running.")
        print("Run: docker-compose up -d postgres redis")
        return 1
    
    # Give services a moment to fully initialize
    print("\n⏳ Waiting for services to initialize...")
    time.sleep(2)
    
    # 3. Check PostgreSQL
    postgres_ok = check_postgres_connection()
    checks.append(("PostgreSQL Connection", postgres_ok))
    
    # 4. Check database migrations
    migrations_ok = check_database_migrations()
    checks.append(("Database Migrations", migrations_ok))
    
    # 5. Check Redis
    redis_ok = check_redis_connection()
    checks.append(("Redis Connection", redis_ok))
    
    # 6. Check Celery worker
    celery_ok = check_celery_worker()
    checks.append(("Celery Worker", celery_ok))
    
    # 7. Check service ports
    ports_ok = check_service_ports()
    checks.append(("Service Ports", ports_ok))
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    
    for check_name, ok in checks:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status:12} {check_name}")
    
    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{total} checks passed")
    print(f"{'=' * 60}")
    
    if passed == total:
        print("\n🎉 All infrastructure checks passed!")
        print("Your DevOps K8s Platform infrastructure is ready.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
