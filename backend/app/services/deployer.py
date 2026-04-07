"""
Deployer Service for applying Kubernetes manifests to clusters
"""

import asyncio
import logging
import time
import yaml
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

from app.schemas import KubernetesManifest, DeploymentStatus

logger = logging.getLogger(__name__)


class DeploymentResult:
    """Result of a deployment operation"""
    
    def __init__(
        self,
        success: bool,
        deployment_id: str,
        applied_manifests: List[str],
        failed_manifests: List[str],
        error_message: Optional[str] = None
    ):
        self.success = success
        self.deployment_id = deployment_id
        self.applied_manifests = applied_manifests
        self.failed_manifests = failed_manifests
        self.error_message = error_message


class HealthCheckResult:
    """Result of post-deployment health checks"""
    
    def __init__(
        self,
        healthy: bool,
        pod_statuses: List[Dict[str, Any]],
        unhealthy_pods: List[Dict[str, Any]],
        message: str
    ):
        self.healthy = healthy
        self.pod_statuses = pod_statuses
        self.unhealthy_pods = unhealthy_pods
        self.message = message


class DeployerService:
    """Service for deploying Kubernetes manifests to clusters"""
    
    def __init__(self, websocket_handler=None, service_account_token: Optional[str] = None):
        """
        Initialize Deployer Service
        
        Args:
            websocket_handler: Optional WebSocket handler for real-time updates
            service_account_token: Optional service account token for RBAC authentication
        """
        self.websocket_handler = websocket_handler
        self.service_account_token = service_account_token
        self.k8s_client = None
        self.apps_v1 = None
        self.core_v1 = None
        self.networking_v1 = None
        self.applied_resources: Set[tuple] = set()  # Track (kind, namespace, name)
    
    def validate_cluster_connectivity(self, cluster_config: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
        """
        Validate connectivity to Kubernetes cluster
        
        Args:
            cluster_config: Optional cluster configuration dict with keys:
                - host: Cluster API server URL
                - token: Service account token (overrides instance token)
                - verify_ssl: Whether to verify SSL certificates (default: True)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Determine authentication method
            if cluster_config and 'token' in cluster_config:
                # Use token from cluster config
                token = cluster_config['token']
                host = cluster_config.get('host')
                verify_ssl = cluster_config.get('verify_ssl', True)
                
                # Create configuration with service account token
                configuration = client.Configuration()
                if host:
                    configuration.host = host
                configuration.api_key = {"authorization": f"Bearer {token}"}
                configuration.verify_ssl = verify_ssl
                
                # Create API client with custom configuration
                self.k8s_client = client.ApiClient(configuration)
                
            elif self.service_account_token:
                # Use instance service account token
                configuration = client.Configuration()
                
                # Try to get cluster host from environment or use default
                if cluster_config and 'host' in cluster_config:
                    configuration.host = cluster_config['host']
                
                configuration.api_key = {"authorization": f"Bearer {self.service_account_token}"}
                configuration.verify_ssl = cluster_config.get('verify_ssl', True) if cluster_config else True
                
                # Create API client with custom configuration
                self.k8s_client = client.ApiClient(configuration)
                
            else:
                # Fall back to kubeconfig or in-cluster config
                try:
                    config.load_kube_config()
                except ConfigException:
                    # Try in-cluster config (when running inside K8s)
                    config.load_incluster_config()
                
                # Create default API client
                self.k8s_client = client.ApiClient()
            
            # Initialize API clients
            self.core_v1 = client.CoreV1Api(self.k8s_client)
            self.apps_v1 = client.AppsV1Api(self.k8s_client)
            self.networking_v1 = client.NetworkingV1Api(self.k8s_client)
            
            # Test connectivity by listing namespaces
            namespaces = self.core_v1.list_namespace(limit=1)
            
            logger.info("Successfully connected to Kubernetes cluster")
            return True, "Successfully connected to Kubernetes cluster"
            
        except ConfigException as e:
            error_msg = f"Failed to load Kubernetes configuration: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except ApiException as e:
            error_msg = f"Failed to connect to Kubernetes API: {e.status} - {e.reason}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error connecting to cluster: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def apply_manifest(
        self,
        manifest: KubernetesManifest,
        namespace: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Apply a single Kubernetes manifest
        
        Args:
            manifest: KubernetesManifest to apply
            namespace: Optional namespace override
            
        Returns:
            Tuple of (success, message)
        """
        if not self.k8s_client:
            return False, "Kubernetes client not initialized. Call validate_cluster_connectivity first."
        
        try:
            # Parse the manifest YAML
            manifest_dict = yaml.safe_load(manifest.content)
            
            if not manifest_dict or not isinstance(manifest_dict, dict):
                return False, f"Invalid manifest content for {manifest.name}"
            
            # Use provided namespace or manifest namespace
            target_namespace = namespace or manifest.namespace or "default"
            
            # Ensure namespace exists in metadata
            if 'metadata' not in manifest_dict:
                manifest_dict['metadata'] = {}
            manifest_dict['metadata']['namespace'] = target_namespace
            
            kind = manifest_dict.get('kind', manifest.kind)
            name = manifest_dict.get('metadata', {}).get('name', manifest.name)
            
            logger.info(f"Applying {kind}/{name} to namespace {target_namespace}")
            
            # Apply based on resource kind
            success, message = self._apply_by_kind(kind, manifest_dict, target_namespace, name)
            
            if success:
                # Track applied resource for potential rollback
                self.applied_resources.add((kind, target_namespace, name))
            
            return success, message
            
        except yaml.YAMLError as e:
            error_msg = f"Failed to parse manifest YAML: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error applying manifest: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _apply_by_kind(
        self,
        kind: str,
        manifest_dict: Dict[str, Any],
        namespace: str,
        name: str
    ) -> tuple[bool, str]:
        """
        Apply manifest based on its kind
        
        Args:
            kind: Kubernetes resource kind
            manifest_dict: Parsed manifest dictionary
            namespace: Target namespace
            name: Resource name
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if kind == "ConfigMap":
                return self._apply_configmap(manifest_dict, namespace, name)
            elif kind == "Secret":
                return self._apply_secret(manifest_dict, namespace, name)
            elif kind == "PersistentVolumeClaim":
                return self._apply_pvc(manifest_dict, namespace, name)
            elif kind == "Deployment":
                return self._apply_deployment(manifest_dict, namespace, name)
            elif kind == "StatefulSet":
                return self._apply_statefulset(manifest_dict, namespace, name)
            elif kind == "Service":
                return self._apply_service(manifest_dict, namespace, name)
            elif kind == "Ingress":
                return self._apply_ingress(manifest_dict, namespace, name)
            else:
                logger.warning(f"Unsupported resource kind: {kind}")
                return False, f"Unsupported resource kind: {kind}"
                
        except ApiException as e:
            error_msg = f"Kubernetes API error: {e.status} - {e.reason}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error applying {kind}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _apply_configmap(self, manifest: Dict, namespace: str, name: str) -> tuple[bool, str]:
        """Apply ConfigMap resource"""
        try:
            # Try to get existing ConfigMap
            try:
                self.core_v1.read_namespaced_config_map(name, namespace)
                # Update existing
                self.core_v1.replace_namespaced_config_map(name, namespace, manifest)
                return True, f"Updated ConfigMap {name}"
            except ApiException as e:
                if e.status == 404:
                    # Create new
                    self.core_v1.create_namespaced_config_map(namespace, manifest)
                    return True, f"Created ConfigMap {name}"
                raise
        except Exception as e:
            return False, str(e)
    
    def _apply_secret(self, manifest: Dict, namespace: str, name: str) -> tuple[bool, str]:
        """Apply Secret resource"""
        try:
            try:
                self.core_v1.read_namespaced_secret(name, namespace)
                self.core_v1.replace_namespaced_secret(name, namespace, manifest)
                return True, f"Updated Secret {name}"
            except ApiException as e:
                if e.status == 404:
                    self.core_v1.create_namespaced_secret(namespace, manifest)
                    return True, f"Created Secret {name}"
                raise
        except Exception as e:
            return False, str(e)
    
    def _apply_pvc(self, manifest: Dict, namespace: str, name: str) -> tuple[bool, str]:
        """Apply PersistentVolumeClaim resource"""
        try:
            try:
                self.core_v1.read_namespaced_persistent_volume_claim(name, namespace)
                # PVCs cannot be updated, only deleted and recreated
                return True, f"PVC {name} already exists"
            except ApiException as e:
                if e.status == 404:
                    self.core_v1.create_namespaced_persistent_volume_claim(namespace, manifest)
                    return True, f"Created PVC {name}"
                raise
        except Exception as e:
            return False, str(e)
    
    def _apply_deployment(self, manifest: Dict, namespace: str, name: str) -> tuple[bool, str]:
        """Apply Deployment resource"""
        try:
            try:
                self.apps_v1.read_namespaced_deployment(name, namespace)
                self.apps_v1.replace_namespaced_deployment(name, namespace, manifest)
                return True, f"Updated Deployment {name}"
            except ApiException as e:
                if e.status == 404:
                    self.apps_v1.create_namespaced_deployment(namespace, manifest)
                    return True, f"Created Deployment {name}"
                raise
        except Exception as e:
            return False, str(e)
    
    def _apply_statefulset(self, manifest: Dict, namespace: str, name: str) -> tuple[bool, str]:
        """Apply StatefulSet resource"""
        try:
            try:
                self.apps_v1.read_namespaced_stateful_set(name, namespace)
                self.apps_v1.replace_namespaced_stateful_set(name, namespace, manifest)
                return True, f"Updated StatefulSet {name}"
            except ApiException as e:
                if e.status == 404:
                    self.apps_v1.create_namespaced_stateful_set(namespace, manifest)
                    return True, f"Created StatefulSet {name}"
                raise
        except Exception as e:
            return False, str(e)
    
    def _apply_service(self, manifest: Dict, namespace: str, name: str) -> tuple[bool, str]:
        """Apply Service resource"""
        try:
            try:
                existing = self.core_v1.read_namespaced_service(name, namespace)
                # Preserve clusterIP for updates
                if 'spec' in manifest and existing.spec.cluster_ip:
                    manifest['spec']['clusterIP'] = existing.spec.cluster_ip
                self.core_v1.replace_namespaced_service(name, namespace, manifest)
                return True, f"Updated Service {name}"
            except ApiException as e:
                if e.status == 404:
                    self.core_v1.create_namespaced_service(namespace, manifest)
                    return True, f"Created Service {name}"
                raise
        except Exception as e:
            return False, str(e)
    
    def _apply_ingress(self, manifest: Dict, namespace: str, name: str) -> tuple[bool, str]:
        """Apply Ingress resource"""
        try:
            try:
                self.networking_v1.read_namespaced_ingress(name, namespace)
                self.networking_v1.replace_namespaced_ingress(name, namespace, manifest)
                return True, f"Updated Ingress {name}"
            except ApiException as e:
                if e.status == 404:
                    self.networking_v1.create_namespaced_ingress(namespace, manifest)
                    return True, f"Created Ingress {name}"
                raise
        except Exception as e:
            return False, str(e)
    
    def _get_dependency_order(self, manifests: List[KubernetesManifest]) -> List[KubernetesManifest]:
        """
        Sort manifests in dependency order for deployment
        
        Order: ConfigMaps/Secrets → PVCs → Deployments/StatefulSets → Services → Ingress
        
        Args:
            manifests: List of manifests to sort
            
        Returns:
            Sorted list of manifests
        """
        order_map = {
            "ConfigMap": 1,
            "Secret": 1,
            "PersistentVolumeClaim": 2,
            "Deployment": 3,
            "StatefulSet": 3,
            "Service": 4,
            "Ingress": 5,
        }
        
        def get_order(manifest: KubernetesManifest) -> int:
            return order_map.get(manifest.kind, 99)
        
        return sorted(manifests, key=get_order)
    
    async def deploy(
        self,
        manifests: List[KubernetesManifest],
        cluster_id: str,
        deployment_id: str,
        namespace: Optional[str] = None
    ) -> DeploymentResult:
        """
        Deploy manifests to Kubernetes cluster with progress tracking
        
        Args:
            manifests: List of Kubernetes manifests to deploy
            cluster_id: Target cluster identifier
            deployment_id: Unique deployment identifier
            namespace: Optional namespace override
            
        Returns:
            DeploymentResult with success status and details
        """
        logger.info(f"Starting deployment {deployment_id} with {len(manifests)} manifests")
        
        # Reset applied resources tracking
        self.applied_resources.clear()
        
        # Validate cluster connectivity
        connected, message = self.validate_cluster_connectivity()
        if not connected:
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                applied_manifests=[],
                failed_manifests=[m.name for m in manifests],
                error_message=message
            )
        
        # Sort manifests in dependency order
        sorted_manifests = self._get_dependency_order(manifests)
        
        applied_manifests = []
        failed_manifests = []
        
        # Apply each manifest
        for i, manifest in enumerate(sorted_manifests):
            try:
                # Send progress update
                if self.websocket_handler:
                    progress = int((i / len(sorted_manifests)) * 100)
                    await self.websocket_handler.send_progress(
                        deployment_id,
                        {
                            "status": "in_progress",
                            "progress": progress,
                            "current_step": f"Applying {manifest.kind}/{manifest.name}",
                            "applied_manifests": applied_manifests,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                # Apply the manifest
                success, msg = self.apply_manifest(manifest, namespace)
                
                if success:
                    applied_manifests.append(f"{manifest.kind}/{manifest.name}")
                    logger.info(f"Successfully applied {manifest.kind}/{manifest.name}")
                else:
                    failed_manifests.append(f"{manifest.kind}/{manifest.name}")
                    logger.error(f"Failed to apply {manifest.kind}/{manifest.name}: {msg}")
                    
                    # Trigger rollback on failure
                    logger.warning(f"Triggering rollback due to failure")
                    rollback_success = await self.rollback(deployment_id, namespace)
                    
                    return DeploymentResult(
                        success=False,
                        deployment_id=deployment_id,
                        applied_manifests=applied_manifests,
                        failed_manifests=failed_manifests,
                        error_message=f"Failed to apply {manifest.kind}/{manifest.name}: {msg}"
                    )
                
            except Exception as e:
                error_msg = f"Unexpected error applying {manifest.kind}/{manifest.name}: {str(e)}"
                logger.error(error_msg)
                failed_manifests.append(f"{manifest.kind}/{manifest.name}")
                
                # Trigger rollback
                await self.rollback(deployment_id, namespace)
                
                return DeploymentResult(
                    success=False,
                    deployment_id=deployment_id,
                    applied_manifests=applied_manifests,
                    failed_manifests=failed_manifests,
                    error_message=error_msg
                )
        
        # All manifests applied successfully
        logger.info(f"Successfully deployed all {len(manifests)} manifests")
        
        return DeploymentResult(
            success=True,
            deployment_id=deployment_id,
            applied_manifests=applied_manifests,
            failed_manifests=[],
            error_message=None
        )

    async def rollback(
        self,
        deployment_id: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Rollback deployment by removing all applied resources
        
        Args:
            deployment_id: Deployment identifier
            namespace: Optional namespace override
            
        Returns:
            True if rollback successful, False otherwise
        """
        logger.info(f"Starting rollback for deployment {deployment_id}")
        
        if not self.applied_resources:
            logger.info("No resources to rollback")
            return True
        
        rollback_success = True
        
        # Remove resources in reverse order
        for kind, ns, name in reversed(list(self.applied_resources)):
            try:
                target_namespace = namespace or ns
                logger.info(f"Removing {kind}/{name} from namespace {target_namespace}")
                
                success, message = self._delete_resource(kind, target_namespace, name)
                
                if not success:
                    logger.error(f"Failed to remove {kind}/{name}: {message}")
                    rollback_success = False
                else:
                    logger.info(f"Successfully removed {kind}/{name}")
                    
            except Exception as e:
                logger.error(f"Error during rollback of {kind}/{name}: {str(e)}")
                rollback_success = False
        
        # Clear applied resources
        self.applied_resources.clear()
        
        if rollback_success:
            logger.info(f"Rollback completed successfully for deployment {deployment_id}")
        else:
            logger.warning(f"Rollback completed with errors for deployment {deployment_id}")
        
        return rollback_success
    
    def _delete_resource(
        self,
        kind: str,
        namespace: str,
        name: str
    ) -> tuple[bool, str]:
        """
        Delete a Kubernetes resource
        
        Args:
            kind: Resource kind
            namespace: Resource namespace
            name: Resource name
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if kind == "ConfigMap":
                self.core_v1.delete_namespaced_config_map(name, namespace)
            elif kind == "Secret":
                self.core_v1.delete_namespaced_secret(name, namespace)
            elif kind == "PersistentVolumeClaim":
                self.core_v1.delete_namespaced_persistent_volume_claim(name, namespace)
            elif kind == "Deployment":
                self.apps_v1.delete_namespaced_deployment(name, namespace)
            elif kind == "StatefulSet":
                self.apps_v1.delete_namespaced_stateful_set(name, namespace)
            elif kind == "Service":
                self.core_v1.delete_namespaced_service(name, namespace)
            elif kind == "Ingress":
                self.networking_v1.delete_namespaced_ingress(name, namespace)
            else:
                return False, f"Unsupported resource kind for deletion: {kind}"
            
            return True, f"Deleted {kind}/{name}"
            
        except ApiException as e:
            if e.status == 404:
                # Resource already deleted
                return True, f"{kind}/{name} not found (already deleted)"
            return False, f"API error: {e.status} - {e.reason}"
        except Exception as e:
            return False, str(e)
    
    async def health_check(
        self,
        namespace: str,
        deployment_id: Optional[str] = None,
        wait_seconds: int = 30
    ) -> HealthCheckResult:
        """
        Perform post-deployment health checks
        
        Args:
            namespace: Namespace to check
            deployment_id: Optional deployment identifier for filtering
            wait_seconds: Seconds to wait before checking (default 30)
            
        Returns:
            HealthCheckResult with health status and pod details
        """
        logger.info(f"Starting health check for namespace {namespace} (waiting {wait_seconds}s)")
        
        # Wait for pods to initialize
        await asyncio.sleep(wait_seconds)
        
        try:
            # Get all pods in namespace
            pods = self.core_v1.list_namespaced_pod(namespace)
            
            pod_statuses = []
            unhealthy_pods = []
            
            for pod in pods.items:
                pod_name = pod.metadata.name
                pod_phase = pod.status.phase
                
                # Check if pod is running
                is_running = pod_phase == "Running"
                
                # Check readiness
                is_ready = False
                if pod.status.conditions:
                    for condition in pod.status.conditions:
                        if condition.type == "Ready":
                            is_ready = condition.status == "True"
                            break
                
                # Get container statuses
                container_statuses = []
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        container_statuses.append({
                            "name": container.name,
                            "ready": container.ready,
                            "restart_count": container.restart_count,
                            "state": self._get_container_state(container.state)
                        })
                
                pod_status = {
                    "name": pod_name,
                    "phase": pod_phase,
                    "is_running": is_running,
                    "is_ready": is_ready,
                    "containers": container_statuses,
                    "node": pod.spec.node_name,
                    "start_time": pod.status.start_time.isoformat() if pod.status.start_time else None
                }
                
                pod_statuses.append(pod_status)
                
                # Track unhealthy pods
                if not is_running or not is_ready:
                    # Get recent events for this pod
                    events = self._get_pod_events(namespace, pod_name)
                    
                    unhealthy_pod = {
                        **pod_status,
                        "events": events
                    }
                    unhealthy_pods.append(unhealthy_pod)
            
            # Determine overall health
            all_healthy = len(unhealthy_pods) == 0
            
            if all_healthy:
                message = f"All {len(pod_statuses)} pods are healthy"
            else:
                message = f"{len(unhealthy_pods)} of {len(pod_statuses)} pods are unhealthy"
            
            logger.info(f"Health check complete: {message}")
            
            return HealthCheckResult(
                healthy=all_healthy,
                pod_statuses=pod_statuses,
                unhealthy_pods=unhealthy_pods,
                message=message
            )
            
        except ApiException as e:
            error_msg = f"Failed to perform health check: {e.status} - {e.reason}"
            logger.error(error_msg)
            return HealthCheckResult(
                healthy=False,
                pod_statuses=[],
                unhealthy_pods=[],
                message=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error during health check: {str(e)}"
            logger.error(error_msg)
            return HealthCheckResult(
                healthy=False,
                pod_statuses=[],
                unhealthy_pods=[],
                message=error_msg
            )
    
    def _get_container_state(self, state) -> str:
        """Get human-readable container state"""
        if state.running:
            return "running"
        elif state.waiting:
            return f"waiting: {state.waiting.reason}"
        elif state.terminated:
            return f"terminated: {state.terminated.reason}"
        return "unknown"
    
    def _get_pod_events(self, namespace: str, pod_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent events for a pod
        
        Args:
            namespace: Pod namespace
            pod_name: Pod name
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        try:
            events = self.core_v1.list_namespaced_event(
                namespace,
                field_selector=f"involvedObject.name={pod_name}"
            )
            
            # Sort by timestamp (most recent first)
            sorted_events = sorted(
                events.items,
                key=lambda e: e.last_timestamp or e.event_time or datetime.min,
                reverse=True
            )
            
            event_list = []
            for event in sorted_events[:limit]:
                event_list.append({
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "timestamp": (event.last_timestamp or event.event_time).isoformat() if (event.last_timestamp or event.event_time) else None,
                    "count": event.count
                })
            
            return event_list
            
        except Exception as e:
            logger.warning(f"Failed to get events for pod {pod_name}: {str(e)}")
            return []
