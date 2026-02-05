"""
Database models for the DevOps K8s Platform
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Float, ForeignKey, 
    LargeBinary, JSON, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Deployment(Base):
    """
    Deployment records for tracking Docker Compose to Kubernetes conversions
    """
    __tablename__ = "deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey("clusters.id"), nullable=False)
    compose_content = Column(Text, nullable=False)
    manifests = Column(JSON, nullable=False)  # Store as JSONB
    status = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    cluster = relationship("Cluster", back_populates="deployments")
    alert_configurations = relationship("AlertConfiguration", back_populates="deployment")


class Cluster(Base):
    """
    Kubernetes cluster configurations
    """
    __tablename__ = "clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'minikube', 'kind', 'gke', 'eks', 'aks'
    config = Column(JSON, nullable=False)  # kubeconfig or connection details
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    deployments = relationship("Deployment", back_populates="cluster")


class LLMConfiguration(Base):
    """
    LLM provider configurations with encrypted API keys
    """
    __tablename__ = "llm_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # 'openai', 'anthropic', 'google', 'ollama'
    api_key_encrypted = Column(LargeBinary, nullable=False)
    endpoint = Column(String(255), nullable=True)  # For custom endpoints like Ollama
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AlertConfiguration(Base):
    """
    Alert configurations for monitoring deployments
    """
    __tablename__ = "alert_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True)
    condition_type = Column(String(50), nullable=False)  # 'cpu_threshold', 'memory_threshold', etc.
    threshold_value = Column(Float, nullable=True)
    notification_channel = Column(String(50), nullable=False)  # 'email', 'webhook', 'in_app'
    notification_config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    deployment = relationship("Deployment", back_populates="alert_configurations")


class Template(Base):
    """
    Pre-built Docker Compose templates for common application stacks
    """
    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)  # 'web', 'database', 'cache', etc.
    compose_content = Column(Text, nullable=False)
    required_params = Column(JSON, nullable=True)  # Parameters user must provide
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """
    User accounts for authentication and authorization
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskStatus(Base):
    """
    Celery task status tracking
    """
    __tablename__ = "task_status"

    id = Column(String(255), primary_key=True)  # Celery task ID
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    task_type = Column(String(50), nullable=False)  # 'conversion', 'deployment', 'analysis'
    status = Column(String(50), nullable=False)  # 'pending', 'in_progress', 'completed', 'failed'
    progress = Column(Integer, default=0)  # 0-100
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())