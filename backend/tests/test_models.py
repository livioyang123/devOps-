#!/usr/bin/env python3
"""
Test script to verify database models and connections
"""

import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, Cluster, Deployment, LLMConfiguration, AlertConfiguration, Template, TaskStatus

def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute("SELECT version()")
            version = result.fetchone()[0]
            print(f"✓ Connected to PostgreSQL: {version}")
            return engine
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return None

def test_models(engine):
    """Test model creation and basic operations"""
    print("\nTesting database models...")
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Test User model
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✓ Created user: {user.email} (ID: {user.id})")
        
        # Test Cluster model
        cluster = Cluster(
            user_id=user.id,
            name="test-cluster",
            type="minikube",
            config={"kubeconfig": "test-config"},
            is_active=True
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
        print(f"✓ Created cluster: {cluster.name} (ID: {cluster.id})")
        
        # Test Deployment model
        deployment = Deployment(
            user_id=user.id,
            name="test-deployment",
            cluster_id=cluster.id,
            compose_content="version: '3.8'\nservices:\n  web:\n    image: nginx",
            manifests={"deployment": "test-manifest"},
            status="pending"
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)
        print(f"✓ Created deployment: {deployment.name} (ID: {deployment.id})")
        
        # Test LLMConfiguration model
        llm_config = LLMConfiguration(
            user_id=user.id,
            provider="openai",
            api_key_encrypted=b"encrypted_key_here",
            is_active=True
        )
        db.add(llm_config)
        db.commit()
        db.refresh(llm_config)
        print(f"✓ Created LLM config: {llm_config.provider} (ID: {llm_config.id})")
        
        # Test AlertConfiguration model
        alert_config = AlertConfiguration(
            user_id=user.id,
            deployment_id=deployment.id,
            condition_type="cpu_threshold",
            threshold_value=80.0,
            notification_channel="email",
            notification_config={"email": "test@example.com"},
            is_active=True
        )
        db.add(alert_config)
        db.commit()
        db.refresh(alert_config)
        print(f"✓ Created alert config: {alert_config.condition_type} (ID: {alert_config.id})")
        
        # Test Template model
        template = Template(
            name="WordPress",
            description="WordPress with MySQL",
            category="web",
            compose_content="version: '3.8'\nservices:\n  wordpress:\n    image: wordpress",
            required_params={"db_password": "string"},
            is_public=True
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        print(f"✓ Created template: {template.name} (ID: {template.id})")
        
        # Test TaskStatus model
        task_status = TaskStatus(
            id="test-task-id",
            user_id=user.id,
            task_type="conversion",
            status="pending",
            progress=0
        )
        db.add(task_status)
        db.commit()
        db.refresh(task_status)
        print(f"✓ Created task status: {task_status.task_type} (ID: {task_status.id})")
        
        # Test relationships
        user_deployments = db.query(Deployment).filter(Deployment.user_id == user.id).all()
        print(f"✓ User has {len(user_deployments)} deployments")
        
        cluster_deployments = db.query(Deployment).filter(Deployment.cluster_id == cluster.id).all()
        print(f"✓ Cluster has {len(cluster_deployments)} deployments")
        
        print("\n✓ All model tests passed!")
        
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Main function"""
    engine = test_database_connection()
    if engine:
        test_models(engine)
    else:
        print("Cannot test models without database connection")

if __name__ == "__main__":
    main()