"""
Example usage of AI Analyzer Service

This script demonstrates how to use the AI Analyzer Service to analyze
Kubernetes logs and detect issues.
"""

import asyncio
from datetime import datetime, timedelta
from app.services.ai_analyzer import AIAnalyzerService
from app.services.llm_router import LLMRouter, ModelParameters
from app.services.llm_providers import OpenAIProvider
from app.schemas import LogEntry


async def main():
    """Example usage of AI Analyzer Service"""
    
    # Create sample logs with various Kubernetes errors
    sample_logs = [
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=10),
            pod_name="web-app-pod-1",
            container_name="nginx",
            message="Starting nginx server",
            level="info"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=9),
            pod_name="web-app-pod-1",
            container_name="nginx",
            message="OOMKilled: Container exceeded memory limit of 512Mi",
            level="error"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=8),
            pod_name="web-app-pod-2",
            container_name="app",
            message="CrashLoopBackOff: Back-off restarting failed container",
            level="error"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=7),
            pod_name="web-app-pod-3",
            container_name="app",
            message="ImagePullBackOff: Failed to pull image 'myapp:latest'",
            level="error"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=6),
            pod_name="web-app-pod-1",
            container_name="nginx",
            message="Restarting container after OOM",
            level="warning"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=5),
            pod_name="database-pod-1",
            container_name="postgres",
            message="Database connection established",
            level="info"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=4),
            pod_name="web-app-pod-2",
            container_name="app",
            message="Error: Cannot connect to database at postgres:5432",
            level="error"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=3),
            pod_name="web-app-pod-1",
            container_name="nginx",
            message="Successfully restarted, serving requests",
            level="info"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=2),
            pod_name="web-app-pod-3",
            container_name="app",
            message="Retrying image pull...",
            level="warning"
        ),
        LogEntry(
            timestamp=datetime.now() - timedelta(minutes=1),
            pod_name="web-app-pod-2",
            container_name="app",
            message="Application startup failed: Missing environment variable DATABASE_URL",
            level="error"
        )
    ]
    
    print("=" * 80)
    print("AI Analyzer Service - Example Usage")
    print("=" * 80)
    print()
    
    # Initialize LLM Router with OpenAI provider
    # Note: In production, get API key from config or environment
    print("Initializing AI Analyzer Service...")
    
    # For this example, we'll use a mock provider
    # In production, use: providers = {"openai": OpenAIProvider(api_key="your-key")}
    from unittest.mock import MagicMock
    
    mock_provider = MagicMock()
    mock_provider.generate.return_value = """
SUMMARY:
Critical issues detected in the deployment. Multiple pods experiencing OOMKilled errors,
CrashLoopBackOff, and ImagePullBackOff. Database connectivity issues also present.

SEVERITY:
critical

ANOMALIES:
critical|Memory exhaustion causing OOM kills|web-app-pod-1
critical|Container startup failures with crash loops|web-app-pod-2
critical|Image pull failures preventing pod startup|web-app-pod-3
warning|Database connectivity issues|web-app-pod-2

RECOMMENDATIONS:
Increase memory limits for web-app-pod-1 to prevent OOM kills
Fix missing DATABASE_URL environment variable in web-app-pod-2
Verify image name and registry credentials for web-app-pod-3
Check network connectivity between application pods and database
Review application startup configuration and dependencies
"""
    
    llm_router = LLMRouter(providers={"mock": mock_provider})
    analyzer = AIAnalyzerService(llm_router)
    
    print(f"Analyzing {len(sample_logs)} log entries...")
    print()
    
    # Perform analysis
    result = analyzer.analyze_logs(
        logs=sample_logs,
        model="mock",
        parameters=ModelParameters(temperature=0.3, max_tokens=2000)
    )
    
    # Display results
    print("=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print()
    
    print(f"Overall Severity: {result.severity.upper()}")
    print()
    
    print("Summary:")
    print("-" * 80)
    print(result.summary)
    print()
    
    print(f"Common Kubernetes Errors Detected: {len(result.common_errors)}")
    print("-" * 80)
    for error in result.common_errors:
        print(f"  • {error.error_type} in {error.pod_name}")
        print(f"    Message: {error.message[:100]}...")
        print(f"    Time: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    print(f"Anomalies Detected: {len(result.anomalies)}")
    print("-" * 80)
    for anomaly in result.anomalies:
        print(f"  • [{anomaly.severity.upper()}] {anomaly.description}")
        if anomaly.affected_pods:
            print(f"    Affected pods: {', '.join(anomaly.affected_pods)}")
        print(f"    Occurrences: {anomaly.occurrences}")
        print()
    
    print(f"Recommendations: {len(result.recommendations)}")
    print("-" * 80)
    for i, recommendation in enumerate(result.recommendations, 1):
        print(f"  {i}. {recommendation}")
    print()
    
    print("=" * 80)
    print("Analysis Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
