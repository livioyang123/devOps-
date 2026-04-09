"""
Application configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # App Info
    app_name: str = "DevOps K8s Platform"
    debug: bool = False
    environment: str = "development"
    
    # Database - ✅ USA POSTGRES, NON LOCALHOST
    database_url: str = "postgresql://devops:devops123@postgres:5432/devops_k8s"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    
    # LLM Providers API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    ollama_endpoint: Optional[str] = None
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Encryption key for API keys storage (32 bytes base64)
    encryption_key: str = "your-encryption-key-change-in-production-32bytes=="
    
    # Rate limiting
    rate_limit_per_minute: int = 60

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Monitoring
    prometheus_url: str = "http://prometheus:9090"
    loki_url: str = "http://loki:3100"
    
    # SMTP for email notifications
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: str = "noreply@devops-k8s-platform.com"
    smtp_use_tls: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()


settings = get_settings()