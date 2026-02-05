"""
Pydantic schemas for request/response models.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# Docker Compose related schemas
class PortMapping(BaseModel):
    """Port mapping configuration."""
    host: Optional[str] = None
    container: str
    protocol: str = "tcp"


class ServiceDefinition(BaseModel):
    """Docker Compose service definition."""
    name: str
    image: Optional[str] = None
    build: Optional[Dict[str, Any]] = None
    ports: List[PortMapping] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)
    volumes: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    command: Optional[str] = None
    networks: List[str] = Field(default_factory=list)


class VolumeDefinition(BaseModel):
    """Docker Compose volume definition."""
    name: str
    driver: Optional[str] = None
    driver_opts: Dict[str, str] = Field(default_factory=dict)
    external: bool = False


class NetworkDefinition(BaseModel):
    """Docker Compose network definition."""
    name: str
    driver: Optional[str] = None
    external: bool = False
    ipam: Optional[Dict[str, Any]] = None


class ComposeStructure(BaseModel):
    """Parsed Docker Compose structure."""
    services: List[ServiceDefinition]
    volumes: List[VolumeDefinition]
    networks: List[NetworkDefinition]
    version: Optional[str] = None


class ValidationError(BaseModel):
    """YAML validation error details."""
    line: Optional[int] = None
    column: Optional[int] = None
    message: str
    error_type: str


class ValidationResult(BaseModel):
    """Result of YAML validation."""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)


class ComposeUploadRequest(BaseModel):
    """Request for uploading Docker Compose content."""
    content: str = Field(..., description="Docker Compose YAML content")


class ComposeParseResponse(BaseModel):
    """Response from parsing Docker Compose."""
    structure: ComposeStructure
    validation: ValidationResult


# Kubernetes related schemas
class KubernetesManifest(BaseModel):
    """Kubernetes manifest representation."""
    kind: str
    name: str
    content: str
    namespace: str = "default"


class ConversionRequest(BaseModel):
    """Request for converting Docker Compose to Kubernetes."""
    compose_structure: ComposeStructure
    model: str
    parameters: Optional[Dict[str, Any]] = None


class ConversionResponse(BaseModel):
    """Response from conversion."""
    manifests: List[KubernetesManifest]
    cached: bool
    conversion_time: float


# Deployment related schemas
class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentRequest(BaseModel):
    """Request for deploying to Kubernetes."""
    manifests: List[KubernetesManifest]
    cluster_id: str
    namespace: str = "default"


class DeploymentResponse(BaseModel):
    """Response from deployment initiation."""
    deployment_id: str
    status: DeploymentStatus
    websocket_url: str


class ProgressUpdate(BaseModel):
    """Real-time deployment progress update."""
    deployment_id: str
    status: DeploymentStatus
    progress: int = Field(..., ge=0, le=100)
    current_step: str
    applied_manifests: List[str]
    timestamp: datetime


# Error response schema
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None


# Monitoring related schemas
class TimeRange(BaseModel):
    """Time range for metrics and logs."""
    start: datetime
    end: datetime


class NetworkMetrics(BaseModel):
    """Network metrics for a pod."""
    rx_bytes: float = Field(..., description="Received bytes")
    tx_bytes: float = Field(..., description="Transmitted bytes")


class PodMetrics(BaseModel):
    """Metrics for a single pod."""
    name: str
    namespace: str
    cpu_usage: float = Field(..., description="CPU usage in cores")
    memory_usage: float = Field(..., description="Memory usage in bytes")
    network: NetworkMetrics
    timestamp: datetime


class ServiceMetrics(BaseModel):
    """Metrics for a service."""
    name: str
    namespace: str
    pods: List[PodMetrics]
    timestamp: datetime


class MetricsData(BaseModel):
    """Complete metrics data response."""
    pods: List[PodMetrics]
    services: List[ServiceMetrics]
    timestamp: datetime


class MetricsRequest(BaseModel):
    """Request for metrics data."""
    deployment_id: str
    time_range: Optional[TimeRange] = None
    namespace: str = "default"


class LogEntry(BaseModel):
    """Single log entry."""
    timestamp: datetime
    pod_name: str
    container_name: str
    message: str
    level: str = "info"


class LogFilters(BaseModel):
    """Filters for log queries."""
    pod_name: Optional[str] = None
    container_name: Optional[str] = None
    level: Optional[str] = None
    search_query: Optional[str] = None


class LogStreamRequest(BaseModel):
    """Request for log streaming."""
    deployment_id: str
    namespace: str = "default"
    filters: Optional[LogFilters] = None
    time_range: Optional[TimeRange] = None


# AI Analysis related schemas
class KubernetesError(BaseModel):
    """Detected Kubernetes error."""
    error_type: str = Field(..., description="Error type: OOMKilled, CrashLoopBackOff, ImagePullBackOff, etc.")
    pod_name: str
    message: str
    timestamp: datetime


class Anomaly(BaseModel):
    """Detected anomaly in logs."""
    description: str
    severity: str = Field(..., description="Severity level: critical, warning, info")
    affected_pods: List[str]
    first_seen: datetime
    occurrences: int


class AnalysisResult(BaseModel):
    """Result of AI log analysis."""
    summary: str
    anomalies: List[Anomaly] = Field(default_factory=list)
    common_errors: List[KubernetesError] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    severity: str = Field(..., description="Overall severity: critical, warning, info, normal")


class AnalysisRequest(BaseModel):
    """Request for AI log analysis."""
    deployment_id: str
    namespace: str = "default"
    time_range: Optional[TimeRange] = None
    model: str = "gpt-4"


# Alert related schemas
class AlertConfigCreate(BaseModel):
    """Request for creating an alert configuration."""
    deployment_id: Optional[str] = None
    condition_type: str = Field(
        ...,
        description="Alert condition type: cpu_threshold, memory_threshold, pod_restart_count, deployment_failure"
    )
    threshold_value: Optional[float] = Field(
        None,
        description="Threshold value for condition (required for threshold-based alerts)"
    )
    notification_channel: str = Field(
        ...,
        description="Notification channel: email, webhook, in_app"
    )
    notification_config: Dict[str, Any] = Field(
        ...,
        description="Channel-specific configuration (e.g., recipient for email, url for webhook)"
    )


class AlertConfigResponse(BaseModel):
    """Response for alert configuration."""
    id: str
    user_id: str
    deployment_id: Optional[str] = None
    condition_type: str
    threshold_value: Optional[float] = None
    notification_channel: str
    notification_config: Dict[str, Any]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TriggeredAlert(BaseModel):
    """Triggered alert details."""
    alert_id: str
    condition_type: str
    threshold_value: Optional[float] = None
    current_value: Optional[float] = None
    message: str
    affected_resource: str
    timestamp: datetime


# Configuration related schemas
class LLMProviderConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(
        ...,
        description="Provider name: openai, anthropic, google, ollama"
    )
    api_key: str = Field(
        ...,
        description="API key for the provider"
    )
    endpoint: Optional[str] = Field(
        None,
        description="Custom endpoint URL (for Ollama or custom deployments)"
    )


class LLMProviderConfigResponse(BaseModel):
    """Response for LLM provider configuration."""
    id: str
    provider: str
    api_key_masked: str = Field(
        ...,
        description="Masked API key for display"
    )
    endpoint: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LLMConfigListResponse(BaseModel):
    """Response for listing LLM configurations."""
    configurations: List[LLMProviderConfigResponse]


class ModelInfo(BaseModel):
    """Information about an available model."""
    id: str = Field(..., description="Model identifier (e.g., 'gpt-4', 'claude-sonnet-3.5')")
    name: str = Field(..., description="Human-readable model name")
    provider: str = Field(..., description="Provider name")
    description: Optional[str] = Field(None, description="Model description")
    max_tokens: int = Field(..., description="Maximum context window size")


class ModelsListResponse(BaseModel):
    """Response for listing available models."""
    models: List[ModelInfo]


class ModelSelectionRequest(BaseModel):
    """Request for selecting a model."""
    model: str = Field(
        ...,
        description="Model identifier to use for AI operations"
    )


class ModelSelectionResponse(BaseModel):
    """Response for model selection."""
    model: str
    message: str


class ModelParameters(BaseModel):
    """Advanced model parameters."""
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)"
    )
    max_tokens: int = Field(
        4000,
        ge=1,
        le=32000,
        description="Maximum tokens to generate"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="Custom system prompt"
    )


class ModelParametersRequest(BaseModel):
    """Request for updating model parameters."""
    parameters: ModelParameters


class ModelParametersResponse(BaseModel):
    """Response for model parameters."""
    parameters: ModelParameters
    message: str


# Cluster related schemas
class ClusterConfig(BaseModel):
    """Cluster configuration request."""
    name: str = Field(
        ...,
        description="Cluster name"
    )
    type: str = Field(
        ...,
        description="Cluster type: minikube, kind, gke, eks, aks"
    )
    config: Dict[str, Any] = Field(
        ...,
        description="Cluster configuration (kubeconfig or connection details)"
    )


class ClusterResponse(BaseModel):
    """Response for cluster configuration."""
    id: str
    name: str
    type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClusterListResponse(BaseModel):
    """Response for listing clusters."""
    clusters: List[ClusterResponse]


# Template related schemas
class TemplateResponse(BaseModel):
    """Response for template information."""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    compose_content: str
    required_params: Optional[Dict[str, Any]] = None
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Response for listing templates."""
    templates: List[TemplateResponse]


class TemplateLoadRequest(BaseModel):
    """Request for loading a template with parameters."""
    template_id: str
    parameters: Optional[Dict[str, str]] = Field(
        None,
        description="Parameter values for template placeholders"
    )


class TemplateLoadResponse(BaseModel):
    """Response for loading a template."""
    template_id: str
    name: str
    compose_content: str
    message: str


# Cost Estimation related schemas
class ResourceRequirements(BaseModel):
    """Resource requirements for a deployment."""
    cpu_cores: float = Field(..., description="Total CPU cores requested")
    memory_gb: float = Field(..., description="Total memory in GB requested")
    storage_gb: float = Field(..., description="Total storage in GB requested")
    pod_count: int = Field(..., description="Number of pods")


class CostBreakdown(BaseModel):
    """Cost breakdown by resource type."""
    cpu_cost: float = Field(..., description="Monthly cost for CPU")
    memory_cost: float = Field(..., description="Monthly cost for memory")
    storage_cost: float = Field(..., description="Monthly cost for storage")
    total_cost: float = Field(..., description="Total monthly cost")


class CostEstimateResponse(BaseModel):
    """Response for cost estimation."""
    deployment_id: str
    cloud_provider: str = Field(..., description="Cloud provider: gke, eks, aks")
    resources: ResourceRequirements
    cost_breakdown: CostBreakdown
    estimated_monthly_cost: float = Field(..., description="Estimated monthly cost in USD")
    disclaimer: str = Field(
        default="This is an approximate estimate based on standard pricing. Actual costs may vary based on region, discounts, and usage patterns.",
        description="Disclaimer about cost accuracy"
    )
    timestamp: datetime
