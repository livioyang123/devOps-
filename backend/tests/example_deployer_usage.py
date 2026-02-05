"""
Example usage of DeployerService

This demonstrates how to use the DeployerService to deploy Kubernetes manifests.
Note: This requires a running Kubernetes cluster (minikube, kind, etc.)
"""

import asyncio
from app.services.deployer import DeployerService
from app.schemas import KubernetesManifest


async def example_deployment():
    """Example deployment workflow"""
    
    print("=" * 60)
    print("DeployerService Usage Example")
    print("=" * 60)
    
    # Initialize deployer
    deployer = DeployerService()
    
    # Step 1: Validate cluster connectivity
    print("\n1. Validating cluster connectivity...")
    connected, message = deployer.validate_cluster_connectivity()
    print(f"   Status: {'✓ Connected' if connected else '✗ Failed'}")
    print(f"   Message: {message}")
    
    if not connected:
        print("\n⚠️  No Kubernetes cluster available. Skipping deployment.")
        print("   To run this example, ensure you have:")
        print("   - minikube, kind, or another K8s cluster running")
        print("   - kubectl configured with valid credentials")
        return
    
    # Step 2: Create sample manifests
    print("\n2. Creating sample Kubernetes manifests...")
    
    configmap_manifest = KubernetesManifest(
        kind="ConfigMap",
        name="app-config",
        content="""apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: default
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
""",
        namespace="default"
    )
    
    deployment_manifest = KubernetesManifest(
        kind="Deployment",
        name="nginx-app",
        content="""apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-app
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
""",
        namespace="default"
    )
    
    service_manifest = KubernetesManifest(
        kind="Service",
        name="nginx-service",
        content="""apiVersion: v1
kind: Service
metadata:
  name: nginx-service
  namespace: default
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
  type: ClusterIP
""",
        namespace="default"
    )
    
    manifests = [configmap_manifest, deployment_manifest, service_manifest]
    print(f"   Created {len(manifests)} manifests")
    
    # Step 3: Deploy manifests
    print("\n3. Deploying manifests to cluster...")
    deployment_id = "example-deployment-001"
    
    result = await deployer.deploy(
        manifests=manifests,
        cluster_id="local-cluster",
        deployment_id=deployment_id,
        namespace="default"
    )
    
    print(f"   Deployment ID: {deployment_id}")
    print(f"   Success: {result.success}")
    print(f"   Applied manifests: {len(result.applied_manifests)}")
    
    if result.applied_manifests:
        for manifest in result.applied_manifests:
            print(f"     ✓ {manifest}")
    
    if result.failed_manifests:
        print(f"   Failed manifests: {len(result.failed_manifests)}")
        for manifest in result.failed_manifests:
            print(f"     ✗ {manifest}")
    
    if result.error_message:
        print(f"   Error: {result.error_message}")
    
    if not result.success:
        print("\n⚠️  Deployment failed. Exiting.")
        return
    
    # Step 4: Perform health check
    print("\n4. Performing post-deployment health check...")
    print("   (Waiting 30 seconds for pods to initialize...)")
    
    health_result = await deployer.health_check(
        namespace="default",
        deployment_id=deployment_id,
        wait_seconds=30
    )
    
    print(f"   Overall health: {'✓ Healthy' if health_result.healthy else '✗ Unhealthy'}")
    print(f"   Message: {health_result.message}")
    print(f"   Total pods: {len(health_result.pod_statuses)}")
    
    if health_result.pod_statuses:
        print("\n   Pod statuses:")
        for pod in health_result.pod_statuses:
            status_icon = "✓" if pod["is_running"] and pod["is_ready"] else "✗"
            print(f"     {status_icon} {pod['name']}: {pod['phase']} (Ready: {pod['is_ready']})")
    
    if health_result.unhealthy_pods:
        print("\n   Unhealthy pods:")
        for pod in health_result.unhealthy_pods:
            print(f"     ✗ {pod['name']}: {pod['phase']}")
            if pod.get('events'):
                print(f"       Recent events:")
                for event in pod['events'][:3]:
                    print(f"         - {event['type']}: {event['reason']} - {event['message']}")
    
    # Step 5: Cleanup (rollback)
    print("\n5. Cleaning up deployment...")
    rollback_success = await deployer.rollback(deployment_id, namespace="default")
    
    if rollback_success:
        print("   ✓ Successfully removed all deployed resources")
    else:
        print("   ⚠️  Rollback completed with some errors")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


async def example_rollback_on_failure():
    """Example demonstrating automatic rollback on failure"""
    
    print("\n" + "=" * 60)
    print("Rollback on Failure Example")
    print("=" * 60)
    
    deployer = DeployerService()
    
    # Validate connectivity
    connected, message = deployer.validate_cluster_connectivity()
    if not connected:
        print(f"\n⚠️  {message}")
        return
    
    print("\n1. Creating manifests with one invalid manifest...")
    
    # Valid ConfigMap
    valid_manifest = KubernetesManifest(
        kind="ConfigMap",
        name="test-config",
        content="""apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  key: value
""",
        namespace="default"
    )
    
    # Invalid manifest (malformed YAML)
    invalid_manifest = KubernetesManifest(
        kind="Deployment",
        name="invalid-deploy",
        content="this is not valid yaml: [[[",
        namespace="default"
    )
    
    manifests = [valid_manifest, invalid_manifest]
    
    print("\n2. Attempting deployment...")
    result = await deployer.deploy(
        manifests=manifests,
        cluster_id="local-cluster",
        deployment_id="rollback-test-001",
        namespace="default"
    )
    
    print(f"   Success: {result.success}")
    print(f"   Applied: {result.applied_manifests}")
    print(f"   Failed: {result.failed_manifests}")
    
    if result.error_message:
        print(f"   Error: {result.error_message}")
    
    print("\n3. Verifying rollback occurred...")
    print(f"   Tracked resources: {len(deployer.applied_resources)}")
    print("   (Should be 0 after automatic rollback)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n🚀 Starting DeployerService examples...\n")
    
    # Run the main deployment example
    asyncio.run(example_deployment())
    
    # Run the rollback example
    asyncio.run(example_rollback_on_failure())
    
    print("\n✅ All examples completed!")
