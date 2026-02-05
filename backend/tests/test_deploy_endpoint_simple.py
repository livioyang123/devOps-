"""
Simple unit tests for Deployment endpoint and task

Tests the core deployment functionality without middleware complexity.

Requirements: 6.1, 6.3, 6.4, 6.5, 6.8, 20.1, 20.2
"""

import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, Cluster, Deployment
from app.schemas import DeploymentRequest, KubernetesManifest, DeploymentStatus
from app.routers.deploy import deploy_manifests, get_deployment_status
from app.auth import TokenData

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_deploy_simple.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_deploy_endpoint_logic():
    """Test the deployment endpoint logic directly"""
    
    print("\nTesting deployment endpoint logic...")
    
    # Create test database
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # Create test user
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create test cluster
        cluster = Cluster(
            id=uuid.uuid4(),
            user_id=user.id,
            name="test-cluster",
            type="minikube",
            config={"kubeconfig": "test-config"},
            is_active=True
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
        
        # Create test manifests
        manifests = [
            KubernetesManifest(
                kind="Deployment",
                name="test-deployment",
                content="apiVersion: apps/v1\nkind: Deployment",
                namespace="default"
            )
        ]
        
        # Create request
        request = DeploymentRequest(
            manifests=manifests,
            cluster_id=str(cluster.id),
            namespace="default"
        )
        
        # Mock current user
        mock_user = TokenData(user_id=str(user.id), email=user.email)
        
        # Mock Celery task
        with patch("app.routers.deploy.deploy_to_kubernetes.apply_async") as mock_task:
            mock_task.return_value = Mock(id="test-task-id")
            
            # Call endpoint function directly
            import asyncio
            response = asyncio.run(deploy_manifests(request, db, mock_user))
            
            # Verify response
            assert response.deployment_id is not None
            assert response.status == DeploymentStatus.IN_PROGRESS
            assert "ws://" in response.websocket_url
            
            # Verify deployment record created
            deployment = db.query(Deployment).filter(
                Deployment.id == uuid.UUID(response.deployment_id)
            ).first()
            
            assert deployment is not None
            assert deployment.cluster_id == cluster.id
            assert deployment.status == DeploymentStatus.IN_PROGRESS.value
            assert len(deployment.manifests) == 1
            
            # Verify Celery task was called
            mock_task.assert_called_once()
            
            print("✓ Deployment endpoint creates deployment record")
            print("✓ Deployment endpoint initiates Celery task")
            print("✓ Deployment endpoint returns correct response")
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_get_deployment_status_logic():
    """Test the get deployment status endpoint logic directly"""
    
    print("\nTesting get deployment status endpoint logic...")
    
    # Create test database
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # Create test user
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create test cluster
        cluster = Cluster(
            id=uuid.uuid4(),
            user_id=user.id,
            name="test-cluster",
            type="minikube",
            config={"kubeconfig": "test-config"},
            is_active=True
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
        
        # Create test deployment
        deployment = Deployment(
            id=uuid.uuid4(),
            user_id=user.id,
            name="test-deployment",
            cluster_id=cluster.id,
            compose_content="",
            manifests=[{"kind": "Deployment", "name": "test"}],
            status=DeploymentStatus.COMPLETED.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deployed_at=datetime.utcnow()
        )
        db.add(deployment)
        db.commit()
        
        # Mock current user
        mock_user = TokenData(user_id=str(user.id), email=user.email)
        
        # Call endpoint function directly
        import asyncio
        response = asyncio.run(get_deployment_status(str(deployment.id), db, mock_user))
        
        # Verify response
        assert response["deployment_id"] == str(deployment.id)
        assert response["status"] == DeploymentStatus.COMPLETED.value
        assert response["cluster_id"] == str(cluster.id)
        assert response["manifest_count"] == 1
        
        print("✓ Get deployment status endpoint returns correct data")
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_deployment_task_integration():
    """Test the deployment task with mocked services"""
    
    print("\nTesting deployment task integration...")
    
    from app.tasks.deployment import deploy_to_kubernetes
    
    # Create test manifests
    manifests = [
        {
            "kind": "Deployment",
            "name": "test-deployment",
            "content": "apiVersion: apps/v1\nkind: Deployment",
            "namespace": "default"
        }
    ]
    
    deployment_id = str(uuid.uuid4())
    cluster_id = str(uuid.uuid4())
    
    # Mock DeployerService
    with patch("app.tasks.deployment.DeployerService") as MockDeployer:
        # Mock deployment result
        mock_deployer_instance = MockDeployer.return_value
        mock_deployer_instance.deploy = AsyncMock(return_value=Mock(
            success=True,
            deployment_id=deployment_id,
            applied_manifests=["Deployment/test-deployment"],
            failed_manifests=[],
            error_message=None
        ))
        mock_deployer_instance.health_check = AsyncMock(return_value=Mock(
            healthy=True,
            pod_statuses=[],
            unhealthy_pods=[],
            message="All pods healthy"
        ))
        
        # Mock database update
        with patch("app.tasks.deployment.update_deployment_status"):
            # Call task
            result = deploy_to_kubernetes(
                manifests=manifests,
                cluster_id=cluster_id,
                deployment_id=deployment_id,
                namespace="default"
            )
            
            # Verify result
            assert result["deployment_id"] == deployment_id
            assert result["status"] == "completed"
            assert result["health_check_passed"] is True
            assert len(result["applied_manifests"]) == 1
            
            print("✓ Deployment task integrates with DeployerService")
            print("✓ Deployment task performs health checks")
            print("✓ Deployment task returns correct result")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Running Deployment Endpoint and Task Tests")
    print("="*60)
    
    test_deploy_endpoint_logic()
    test_get_deployment_status_logic()
    test_deployment_task_integration()
    
    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60 + "\n")
