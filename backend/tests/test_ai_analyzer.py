"""
Unit tests for AI Analyzer Service and API endpoint
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User, Deployment
from app.schemas import (
    LogEntry,
    AnalysisRequest,
    AnalysisResult,
    KubernetesError,
    Anomaly,
    TimeRange
)
from app.services.ai_analyzer import AIAnalyzerService
from app.services.llm_router import LLMRouter, ModelParameters
from app.auth import TokenData, get_current_user
import uuid


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_ai_analyzer.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db():
    """Create test database and tables"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def mock_current_user(test_user):
    """Mock current user authentication"""
    return TokenData(user_id=str(test_user.id), email=test_user.email)


@pytest.fixture
def mock_deployment(test_db, test_user):
    """Create mock deployment."""
    deployment = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="test-deployment",
        cluster_id=uuid.uuid4(),
        compose_content="",
        manifests=[],
        status="completed"
    )
    test_db.add(deployment)
    test_db.commit()
    test_db.refresh(deployment)
    return deployment


@pytest.fixture
def sample_logs():
    """Create sample log entries for testing"""
    now = datetime.utcnow()
    return [
        LogEntry(
            timestamp=now - timedelta(minutes=5),
            pod_name="test-pod-1",
            container_name="app",
            message="Application started successfully",
            level="info"
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=4),
            pod_name="test-pod-1",
            container_name="app",
            message="OOMKilled: Container exceeded memory limit",
            level="error"
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=3),
            pod_name="test-pod-2",
            container_name="app",
            message="CrashLoopBackOff: Back-off restarting failed container",
            level="error"
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=2),
            pod_name="test-pod-3",
            container_name="app",
            message="ImagePullBackOff: Failed to pull image",
            level="error"
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=1),
            pod_name="test-pod-1",
            container_name="app",
            message="Processing request",
            level="info"
        )
    ]


@pytest.fixture
def mock_llm_router():
    """Create mock LLM router"""
    router = MagicMock(spec=LLMRouter)
    router.generate.return_value = """
SUMMARY:
Multiple critical errors detected including OOMKilled, CrashLoopBackOff, and ImagePullBackOff. 
The system is experiencing resource constraints and container startup failures.

SEVERITY:
critical

ANOMALIES:
critical|Memory exhaustion in test-pod-1|test-pod-1
warning|Repeated container restarts in test-pod-2|test-pod-2
critical|Image pull failures in test-pod-3|test-pod-3

RECOMMENDATIONS:
Increase memory limits for affected containers
Verify image registry credentials and network connectivity
Review application startup configuration and dependencies
"""
    return router


class TestAIAnalyzerService:
    """Test AI Analyzer Service"""
    
    def test_detect_common_errors_oomkilled(self, sample_logs, mock_llm_router):
        """Test detection of OOMKilled errors"""
        analyzer = AIAnalyzerService(mock_llm_router)
        errors = analyzer.detect_common_errors(sample_logs)
        
        # Should detect OOMKilled error
        oom_errors = [e for e in errors if e.error_type == "OOMKilled"]
        assert len(oom_errors) == 1
        assert oom_errors[0].pod_name == "test-pod-1"
        assert "OOMKilled" in oom_errors[0].message
    
    def test_detect_common_errors_crashloop(self, sample_logs, mock_llm_router):
        """Test detection of CrashLoopBackOff errors"""
        analyzer = AIAnalyzerService(mock_llm_router)
        errors = analyzer.detect_common_errors(sample_logs)
        
        # Should detect CrashLoopBackOff error
        crash_errors = [e for e in errors if e.error_type == "CrashLoopBackOff"]
        assert len(crash_errors) == 1
        assert crash_errors[0].pod_name == "test-pod-2"
    
    def test_detect_common_errors_imagepull(self, sample_logs, mock_llm_router):
        """Test detection of ImagePullBackOff errors"""
        analyzer = AIAnalyzerService(mock_llm_router)
        errors = analyzer.detect_common_errors(sample_logs)
        
        # Should detect ImagePullBackOff error
        image_errors = [e for e in errors if e.error_type == "ImagePullBackOff"]
        assert len(image_errors) == 1
        assert image_errors[0].pod_name == "test-pod-3"
    
    def test_generate_recommendations_oomkilled(self, mock_llm_router):
        """Test recommendation generation for OOMKilled errors"""
        analyzer = AIAnalyzerService(mock_llm_router)
        
        errors = [
            KubernetesError(
                error_type="OOMKilled",
                pod_name="test-pod",
                message="OOMKilled",
                timestamp=datetime.utcnow()
            )
        ]
        
        recommendations = analyzer.generate_recommendations(errors)
        
        # Should include memory-related recommendation
        assert any("memory" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_crashloop(self, mock_llm_router):
        """Test recommendation generation for CrashLoopBackOff errors"""
        analyzer = AIAnalyzerService(mock_llm_router)
        
        errors = [
            KubernetesError(
                error_type="CrashLoopBackOff",
                pod_name="test-pod",
                message="CrashLoopBackOff",
                timestamp=datetime.utcnow()
            )
        ]
        
        recommendations = analyzer.generate_recommendations(errors)
        
        # Should include startup-related recommendation
        assert any("startup" in rec.lower() or "configuration" in rec.lower() for rec in recommendations)
    
    def test_analyze_logs_with_llm(self, sample_logs, mock_llm_router):
        """Test full log analysis with LLM"""
        analyzer = AIAnalyzerService(mock_llm_router)
        
        result = analyzer.analyze_logs(
            logs=sample_logs,
            model="gpt-4",
            parameters=ModelParameters(temperature=0.3, max_tokens=2000)
        )
        
        # Verify LLM was called
        assert mock_llm_router.generate.called
        
        # Verify result structure
        assert isinstance(result, AnalysisResult)
        assert result.summary
        assert result.severity in ["critical", "warning", "info", "normal"]
        assert len(result.common_errors) == 3  # OOMKilled, CrashLoopBackOff, ImagePullBackOff
        assert len(result.anomalies) > 0
        assert len(result.recommendations) > 0
    
    def test_analyze_logs_llm_failure(self, sample_logs, mock_llm_router):
        """Test log analysis when LLM fails"""
        # Make LLM router raise an exception
        mock_llm_router.generate.side_effect = Exception("LLM API error")
        
        analyzer = AIAnalyzerService(mock_llm_router)
        
        result = analyzer.analyze_logs(
            logs=sample_logs,
            model="gpt-4"
        )
        
        # Should still return result with detected errors
        assert isinstance(result, AnalysisResult)
        assert len(result.common_errors) == 3
        assert result.severity in ["warning", "info"]
        assert "failed" in result.summary.lower() or "error" in result.summary.lower()
    
    def test_prepare_log_context(self, sample_logs, mock_llm_router):
        """Test log context preparation"""
        analyzer = AIAnalyzerService(mock_llm_router)
        
        context = analyzer._prepare_log_context(sample_logs, max_entries=3)
        
        # Should format logs properly
        assert "test-pod-1" in context
        assert "test-pod-2" in context
        assert "test-pod-3" in context
        
        # Should limit to max_entries
        lines = context.split("\n")
        assert len(lines) <= 3


class TestAnalyzeLogsEndpoint:
    """Test /api/analyze-logs endpoint"""
    
    @pytest.fixture
    def client(self, mock_current_user):
        """Create test client with auth override."""
        def override_get_current_user():
            return mock_current_user
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        client = TestClient(app)
        yield client
        
        # Clean up overrides
        app.dependency_overrides.clear()
    
    @patch("app.routers.monitor.get_monitor_service")
    @patch("app.routers.monitor.get_ai_analyzer_service")
    @patch("app.routers.monitor.LLMRouter")
    def test_analyze_logs_success(
        self,
        mock_llm_router_class,
        mock_get_analyzer,
        mock_get_monitor,
        client,
        mock_deployment,
        sample_logs
    ):
        """Test successful log analysis"""
        # Mock monitor service to return logs
        mock_monitor = AsyncMock()
        
        async def mock_stream_logs(*args, **kwargs):
            for log in sample_logs:
                yield log
        
        mock_monitor.stream_logs = mock_stream_logs
        mock_get_monitor.return_value = mock_monitor
        
        # Mock AI analyzer service
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_logs.return_value = AnalysisResult(
            summary="Test analysis summary",
            anomalies=[],
            common_errors=[
                KubernetesError(
                    error_type="OOMKilled",
                    pod_name="test-pod",
                    message="OOMKilled",
                    timestamp=datetime.utcnow()
                )
            ],
            recommendations=["Increase memory limits"],
            severity="warning"
        )
        mock_get_analyzer.return_value = mock_analyzer
        
        # Make request
        response = client.post(
            "/api/analyze-logs",
            json={
                "deployment_id": str(mock_deployment.id),
                "namespace": "default",
                "model": "gpt-4"
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Test analysis summary"
        assert data["severity"] == "warning"
        assert len(data["common_errors"]) == 1
        assert data["common_errors"][0]["error_type"] == "OOMKilled"
    
    def test_analyze_logs_deployment_not_found(self, client):
        """Test analysis with non-existent deployment"""
        response = client.post(
            "/api/analyze-logs",
            json={
                "deployment_id": str(uuid.uuid4()),
                "namespace": "default",
                "model": "gpt-4"
            }
        )
        
        # Should return 404
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
