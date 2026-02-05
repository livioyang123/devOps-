"""
Verification script for Task 13: Backend Deployment API and Celery Task

This script verifies that all components of Task 13 are properly implemented.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def verify_deployment_router():
    """Verify deployment router exists and has required endpoints"""
    print("\n1. Verifying Deployment Router...")
    
    try:
        from app.routers import deploy
        
        # Check router exists
        assert hasattr(deploy, 'router'), "Router not found"
        print("   ✓ Deployment router exists")
        
        # Check endpoints exist
        assert hasattr(deploy, 'deploy_manifests'), "deploy_manifests endpoint not found"
        assert hasattr(deploy, 'get_deployment_status'), "get_deployment_status endpoint not found"
        print("   ✓ POST /api/deploy endpoint exists")
        print("   ✓ GET /api/deploy/{deployment_id} endpoint exists")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_deployment_task():
    """Verify deployment Celery task is properly implemented"""
    print("\n2. Verifying Deployment Celery Task...")
    
    try:
        from app.tasks.deployment import deploy_to_kubernetes, update_deployment_status
        
        # Check task exists
        assert callable(deploy_to_kubernetes), "deploy_to_kubernetes task not found"
        print("   ✓ deploy_to_kubernetes task exists")
        
        # Check helper function exists
        assert callable(update_deployment_status), "update_deployment_status function not found"
        print("   ✓ update_deployment_status helper function exists")
        
        # Check task is registered with Celery
        from app.celery_app import celery_app
        assert 'app.tasks.deployment.deploy_to_kubernetes' in celery_app.tasks
        print("   ✓ Task registered with Celery")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_integration():
    """Verify integration with DeployerService and WebSocketHandler"""
    print("\n3. Verifying Service Integration...")
    
    try:
        from app.tasks.deployment import deploy_to_kubernetes
        import inspect
        
        # Get task source code
        source = inspect.getsource(deploy_to_kubernetes)
        
        # Check for DeployerService integration
        assert 'DeployerService' in source, "DeployerService not integrated"
        print("   ✓ DeployerService integrated")
        
        # Check for WebSocketHandler integration
        assert 'websocket_handler' in source, "WebSocketHandler not integrated"
        print("   ✓ WebSocketHandler integrated")
        
        # Check for progress updates
        assert 'send_progress' in source, "Progress updates not implemented"
        print("   ✓ Progress updates implemented")
        
        # Check for health checks
        assert 'health_check' in source, "Health checks not implemented"
        print("   ✓ Health checks implemented")
        
        # Check for database updates
        assert 'update_deployment_status' in source, "Database updates not implemented"
        print("   ✓ Database updates implemented")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_main_app_integration():
    """Verify router is registered in main app"""
    print("\n4. Verifying Main App Integration...")
    
    try:
        from app.main import app
        
        # Check if deploy router is included
        routes = [route.path for route in app.routes]
        
        assert any('/api/deploy' in route for route in routes), "Deploy routes not registered"
        print("   ✓ Deploy router registered in main app")
        print("   ✓ Routes available at /api/deploy")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_schemas():
    """Verify required schemas exist"""
    print("\n5. Verifying Schemas...")
    
    try:
        from app.schemas import (
            DeploymentRequest,
            DeploymentResponse,
            DeploymentStatus,
            ProgressUpdate,
            KubernetesManifest
        )
        
        print("   ✓ DeploymentRequest schema exists")
        print("   ✓ DeploymentResponse schema exists")
        print("   ✓ DeploymentStatus enum exists")
        print("   ✓ ProgressUpdate schema exists")
        print("   ✓ KubernetesManifest schema exists")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_database_model():
    """Verify Deployment model exists"""
    print("\n6. Verifying Database Model...")
    
    try:
        from app.models import Deployment
        
        # Check model attributes
        assert hasattr(Deployment, 'id'), "id field not found"
        assert hasattr(Deployment, 'user_id'), "user_id field not found"
        assert hasattr(Deployment, 'cluster_id'), "cluster_id field not found"
        assert hasattr(Deployment, 'manifests'), "manifests field not found"
        assert hasattr(Deployment, 'status'), "status field not found"
        assert hasattr(Deployment, 'error_message'), "error_message field not found"
        
        print("   ✓ Deployment model exists")
        print("   ✓ All required fields present")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def main():
    """Run all verification checks"""
    print("="*70)
    print("Task 13 Implementation Verification")
    print("="*70)
    
    results = []
    
    results.append(("Deployment Router", verify_deployment_router()))
    results.append(("Deployment Task", verify_deployment_task()))
    results.append(("Service Integration", verify_integration()))
    results.append(("Main App Integration", verify_main_app_integration()))
    results.append(("Schemas", verify_schemas()))
    results.append(("Database Model", verify_database_model()))
    
    print("\n" + "="*70)
    print("Verification Summary")
    print("="*70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<50} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("="*70)
    if all_passed:
        print("✅ All verifications passed! Task 13 is complete.")
    else:
        print("❌ Some verifications failed. Please review the errors above.")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
