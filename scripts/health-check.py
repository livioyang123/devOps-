#!/usr/bin/env python3
"""
Health check script for DevOps K8s Platform
Verifies that all components are properly configured
"""

import os
import sys
import subprocess
from pathlib import Path

def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (missing)")
        return False

def check_directory_exists(dir_path: str, description: str) -> bool:
    """Check if a directory exists"""
    if os.path.isdir(dir_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} (missing)")
        return False

def check_npm_dependencies() -> bool:
    """Check if npm dependencies are installed"""
    try:
        result = subprocess.run(
            ["npm", "list", "--depth=0"], 
            cwd="frontend", 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print("✅ Frontend dependencies: Installed")
            return True
        else:
            print("❌ Frontend dependencies: Not installed or issues found")
            return False
    except Exception as e:
        print(f"❌ Frontend dependencies: Error checking - {e}")
        return False

def main():
    """Main health check function"""
    print("🔍 DevOps K8s Platform - Health Check")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 0
    
    # Check project structure
    structure_checks = [
        ("frontend", "Frontend directory"),
        ("backend", "Backend directory"),
        ("infra", "Infrastructure directory"),
        ("docker-compose.yml", "Docker Compose file"),
        ("README.md", "README file"),
        ("Makefile", "Makefile"),
    ]
    
    print("\n📁 Project Structure:")
    for path, desc in structure_checks:
        total_checks += 1
        if check_directory_exists(path, desc) if os.path.isdir(path) else check_file_exists(path, desc):
            checks_passed += 1
    
    # Check frontend files
    frontend_checks = [
        ("frontend/package.json", "Frontend package.json"),
        ("frontend/src/app/layout.tsx", "Frontend layout"),
        ("frontend/src/app/page.tsx", "Frontend main page"),
        ("frontend/src/components/ui", "shadcn/ui components"),
        ("frontend/.env.local", "Frontend environment"),
    ]
    
    print("\n🎨 Frontend Files:")
    for path, desc in frontend_checks:
        total_checks += 1
        if check_file_exists(path, desc) if not os.path.isdir(path) else check_directory_exists(path, desc):
            checks_passed += 1
    
    # Check backend files
    backend_checks = [
        ("backend/requirements.txt", "Backend requirements"),
        ("backend/app/main.py", "Backend main app"),
        ("backend/app/config.py", "Backend configuration"),
        ("backend/pyproject.toml", "Backend project config"),
        ("backend/.env", "Backend environment"),
    ]
    
    print("\n⚙️ Backend Files:")
    for path, desc in backend_checks:
        total_checks += 1
        if check_file_exists(path, desc):
            checks_passed += 1
    
    # Check infrastructure files
    infra_checks = [
        ("infra/prometheus/prometheus.yml", "Prometheus config"),
        ("infra/loki/loki-config.yml", "Loki config"),
        ("infra/grafana/provisioning/datasources/datasources.yml", "Grafana datasources"),
        ("infra/postgres/init.sql", "PostgreSQL init script"),
    ]
    
    print("\n🏗️ Infrastructure Files:")
    for path, desc in infra_checks:
        total_checks += 1
        if check_file_exists(path, desc):
            checks_passed += 1
    
    # Check npm dependencies
    print("\n📦 Dependencies:")
    total_checks += 1
    if check_npm_dependencies():
        checks_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Health Check Summary: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🎉 All checks passed! Your DevOps K8s Platform is ready for development.")
        return 0
    else:
        print("⚠️ Some checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())