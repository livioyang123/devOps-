# DeployerService Implementation

## Overview

The `DeployerService` is responsible for deploying Kubernetes manifests to target clusters. It provides functionality for:

- Validating cluster connectivity
- Applying manifests in dependency order
- Automatic rollback on deployment failures
- Post-deployment health checks
- Real-time progress updates via WebSocket

## Architecture

### Core Components

1. **DeployerService**: Main service class for deployment operations
2. **DeploymentResult**: Result object containing deployment status and details
3. **HealthCheckResult**: Result object containing health check information

### Dependencies

- `kubernetes`: Python Kubernetes client library
- `pyyaml`: YAML parsing
- `asyncio`: Asynchronous operations

## Key Features

### 1. Cluster Connectivity Validation

The service validates connectivity to Kubernetes clusters before attempting deployment:

```python
deployer = DeployerService()
connected, message = deployer.validate_cluster_connectivity()

if connected:
    print("Successfully connected to cluster")
else:
    print(f"Connection failed: {message}")
```

**Supported cluster types:**
- Local clusters (minikube, kind)
- Cloud clusters (GKE, EKS, AKS)
- In-cluster configuration (when running inside Kubernetes)

### 2. Manifest Application in Dependency Order

Manifests are automatically sorted and applied in the correct dependency order:

1. **ConfigMaps and Secrets** - Configuration data
2. **PersistentVolumeClaims** - Storage resources
3. **Deployments and StatefulSets** - Application workloads
4. **Services** - Network exposure
5. **Ingress** - External access

```python
# Manifests are automatically sorted
sorted_manifests = deployer._get_dependency_order(manifests)
```

### 3. Automatic Rollback on Failure

If any manifest fails to apply, the service automatically rolls back all successfully applied resources:

```python
result = await deployer.deploy(
    manifests=manifests,
    cluster_id="cluster-id",
    deployment_id="deployment-id"
)

if not result.success:
    # Rollback was automatically triggered
    print(f"Deployment failed: {result.error_message}")
    print(f"Rolled back: {result.applied_manifests}")
```

### 4. Post-Deployment Health Checks

After deployment, the service performs comprehensive health checks:

```python
health_result = await deployer.health_check(
    namespace="default",
    wait_seconds=30  # Wait for pods to initialize
)

if health_result.healthy:
    print("All pods are healthy")
else:
    print(f"Unhealthy pods: {len(health_result.unhealthy_pods)}")
    for pod in health_result.unhealthy_pods:
        print(f"  - {pod['name']}: {pod['phase']}")
        for event in pod['events']:
            print(f"    {event['reason']}: {event['message']}")
```

**Health check criteria:**
- Pod phase is "Running"
- Readiness probes are passing
- Container statuses are healthy
- Recent events are captured for unhealthy pods

### 5. Real-Time Progress Updates

The service supports WebSocket integration for real-time deployment progress:

```python
deployer = DeployerService(websocket_handler=ws_handler)

# Progress updates are automatically sent during deployment
result = await deployer.deploy(manifests, cluster_id, deployment_id)
```

## API Reference

### DeployerService

#### `__init__(websocket_handler=None)`

Initialize the deployer service.

**Parameters:**
- `websocket_handler` (optional): WebSocket handler for real-time updates

#### `validate_cluster_connectivity(cluster_config=None) -> tuple[bool, str]`

Validate connectivity to Kubernetes cluster.

**Parameters:**
- `cluster_config` (optional): Cluster configuration dictionary

**Returns:**
- Tuple of (success: bool, message: str)

#### `apply_manifest(manifest, namespace=None) -> tuple[bool, str]`

Apply a single Kubernetes manifest.

**Parameters:**
- `manifest`: KubernetesManifest object
- `namespace` (optional): Namespace override

**Returns:**
- Tuple of (success: bool, message: str)

#### `async deploy(manifests, cluster_id, deployment_id, namespace=None) -> DeploymentResult`

Deploy manifests to Kubernetes cluster.

**Parameters:**
- `manifests`: List of KubernetesManifest objects
- `cluster_id`: Target cluster identifier
- `deployment_id`: Unique deployment identifier
- `namespace` (optional): Namespace override

**Returns:**
- DeploymentResult object

#### `async rollback(deployment_id, namespace=None) -> bool`

Rollback deployment by removing all applied resources.

**Parameters:**
- `deployment_id`: Deployment identifier
- `namespace` (optional): Namespace override

**Returns:**
- True if rollback successful, False otherwise

#### `async health_check(namespace, deployment_id=None, wait_seconds=30) -> HealthCheckResult`

Perform post-deployment health checks.

**Parameters:**
- `namespace`: Namespace to check
- `deployment_id` (optional): Deployment identifier for filtering
- `wait_seconds`: Seconds to wait before checking (default 30)

**Returns:**
- HealthCheckResult object

### DeploymentResult

Result object containing deployment status and details.

**Attributes:**
- `success` (bool): Whether deployment succeeded
- `deployment_id` (str): Deployment identifier
- `applied_manifests` (List[str]): List of successfully applied manifests
- `failed_manifests` (List[str]): List of failed manifests
- `error_message` (Optional[str]): Error message if deployment failed

### HealthCheckResult

Result object containing health check information.

**Attributes:**
- `healthy` (bool): Whether all pods are healthy
- `pod_statuses` (List[Dict]): Status information for all pods
- `unhealthy_pods` (List[Dict]): Detailed information for unhealthy pods
- `message` (str): Summary message

## Supported Resource Types

The DeployerService supports the following Kubernetes resource types:

- **ConfigMap**: Configuration data
- **Secret**: Sensitive data
- **PersistentVolumeClaim**: Storage requests
- **Deployment**: Stateless applications
- **StatefulSet**: Stateful applications
- **Service**: Network exposure
- **Ingress**: External HTTP/HTTPS access

## Error Handling

The service provides comprehensive error handling:

1. **Connection Errors**: Cluster connectivity issues
2. **API Errors**: Kubernetes API failures
3. **YAML Errors**: Invalid manifest content
4. **Resource Errors**: Resource creation/update failures

All errors are logged and returned with descriptive messages.

## Usage Examples

### Basic Deployment

```python
import asyncio
from app.services.deployer import DeployerService
from app.schemas import KubernetesManifest

async def deploy_app():
    deployer = DeployerService()
    
    # Validate connectivity
    connected, message = deployer.validate_cluster_connectivity()
    if not connected:
        print(f"Failed to connect: {message}")
        return
    
    # Create manifests
    manifests = [
        KubernetesManifest(
            kind="Deployment",
            name="my-app",
            content=deployment_yaml,
            namespace="default"
        ),
        KubernetesManifest(
            kind="Service",
            name="my-app-service",
            content=service_yaml,
            namespace="default"
        )
    ]
    
    # Deploy
    result = await deployer.deploy(
        manifests=manifests,
        cluster_id="my-cluster",
        deployment_id="deploy-001"
    )
    
    if result.success:
        print("Deployment successful!")
        
        # Perform health check
        health = await deployer.health_check("default")
        print(f"Health: {health.message}")
    else:
        print(f"Deployment failed: {result.error_message}")

asyncio.run(deploy_app())
```

### Deployment with Rollback

```python
async def deploy_with_rollback():
    deployer = DeployerService()
    
    result = await deployer.deploy(manifests, cluster_id, deployment_id)
    
    if not result.success:
        # Automatic rollback already occurred
        print(f"Deployment failed and rolled back")
        print(f"Applied before failure: {result.applied_manifests}")
        print(f"Error: {result.error_message}")
```

### Manual Rollback

```python
async def manual_rollback():
    deployer = DeployerService()
    
    # Deploy
    result = await deployer.deploy(manifests, cluster_id, deployment_id)
    
    # Later, manually rollback
    success = await deployer.rollback(deployment_id, namespace="default")
    
    if success:
        print("Rollback completed successfully")
```

## Testing

The DeployerService includes comprehensive unit tests:

```bash
# Run tests
cd backend
python -m pytest tests/test_deployer_service.py -v

# Run example usage (requires running K8s cluster)
python tests/example_deployer_usage.py
```

## Integration with Other Services

The DeployerService integrates with:

1. **ConverterService**: Receives generated Kubernetes manifests
2. **WebSocketHandler**: Sends real-time progress updates
3. **Celery**: Runs deployment as asynchronous task
4. **Database**: Stores deployment records and status

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 5.4**: Cluster connectivity validation
- **Requirement 5.5**: Connection error handling
- **Requirement 6.1**: Manifest application to cluster
- **Requirement 6.2**: Kubernetes API/kubectl integration
- **Requirement 6.6**: Automatic rollback on failure
- **Requirement 6.7**: Resource removal during rollback
- **Requirement 18.1**: 30-second wait after deployment
- **Requirement 18.2**: Pod status checking
- **Requirement 18.3**: Running state verification
- **Requirement 18.4**: Readiness probe checking
- **Requirement 18.5**: Unhealthy pod reporting
- **Requirement 18.6**: Event capture for unhealthy pods

## Future Enhancements

Potential improvements for future versions:

1. Support for additional resource types (DaemonSet, Job, CronJob)
2. Helm chart deployment support
3. Blue-green deployment strategies
4. Canary deployment support
5. Resource usage monitoring during deployment
6. Deployment history and versioning
7. Multi-cluster deployment orchestration

## Troubleshooting

### Common Issues

**Issue**: "Failed to load Kubernetes configuration"
- **Solution**: Ensure kubeconfig is properly configured at `~/.kube/config`

**Issue**: "Failed to connect to Kubernetes API"
- **Solution**: Verify cluster is running and accessible

**Issue**: "Deployment failed with API error"
- **Solution**: Check Kubernetes API server logs and resource quotas

**Issue**: "Health check reports unhealthy pods"
- **Solution**: Review pod events and logs for specific error messages

## References

- [Kubernetes Python Client Documentation](https://github.com/kubernetes-client/python)
- [Kubernetes API Reference](https://kubernetes.io/docs/reference/kubernetes-api/)
- [Design Document](../../.kiro/specs/devops-k8s-platform/design.md)
- [Requirements Document](../../.kiro/specs/devops-k8s-platform/requirements.md)
