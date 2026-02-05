"""
Example usage of WebSocket Handler for real-time deployment updates.

This script demonstrates how to use the WebSocket handler to broadcast
deployment progress updates to connected clients.

Requirements: 6.3, 6.4, 7.2
"""
import asyncio
from datetime import datetime

from app.services.websocket_handler import websocket_handler
from app.schemas import ProgressUpdate, DeploymentStatus


async def simulate_deployment_with_websocket(deployment_id: str):
    """
    Simulate a deployment operation with WebSocket progress updates.
    
    This example shows how a deployment task would use the WebSocket
    handler to broadcast real-time updates to connected clients.
    
    Args:
        deployment_id: Unique identifier for the deployment
    """
    print(f"\n=== Simulating Deployment: {deployment_id} ===\n")
    
    # Step 1: Send initial progress update
    print("Step 1: Starting deployment...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=10,
        current_step="Validating manifests",
        applied_manifests=[],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(1)
    
    # Step 2: Apply ConfigMap
    print("Step 2: Applying ConfigMap...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=25,
        current_step="Applying ConfigMap manifest",
        applied_manifests=["configmap-app-config"],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(1)
    
    # Step 3: Apply Secret
    print("Step 3: Applying Secret...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=40,
        current_step="Applying Secret manifest",
        applied_manifests=["configmap-app-config", "secret-app-secrets"],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(1)
    
    # Step 4: Apply Deployment
    print("Step 4: Applying Deployment...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=60,
        current_step="Applying Deployment manifest",
        applied_manifests=[
            "configmap-app-config",
            "secret-app-secrets",
            "deployment-web"
        ],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(1)
    
    # Step 5: Apply Service
    print("Step 5: Applying Service...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=80,
        current_step="Applying Service manifest",
        applied_manifests=[
            "configmap-app-config",
            "secret-app-secrets",
            "deployment-web",
            "service-web"
        ],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(1)
    
    # Step 6: Health checks
    print("Step 6: Running health checks...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=95,
        current_step="Running post-deployment health checks",
        applied_manifests=[
            "configmap-app-config",
            "secret-app-secrets",
            "deployment-web",
            "service-web"
        ],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(2)
    
    # Step 7: Completion
    print("Step 7: Deployment completed!")
    await websocket_handler.send_completion(
        deployment_id=deployment_id,
        status=DeploymentStatus.COMPLETED,
        message="Deployment completed successfully",
        details={
            "total_manifests": 4,
            "pods_healthy": 3,
            "services_created": 1,
            "duration_seconds": 7
        }
    )
    
    print(f"\n=== Deployment {deployment_id} Complete ===\n")


async def simulate_failed_deployment(deployment_id: str):
    """
    Simulate a failed deployment with rollback.
    
    Args:
        deployment_id: Unique identifier for the deployment
    """
    print(f"\n=== Simulating Failed Deployment: {deployment_id} ===\n")
    
    # Step 1: Start deployment
    print("Step 1: Starting deployment...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=10,
        current_step="Validating manifests",
        applied_manifests=[],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(1)
    
    # Step 2: Apply some manifests
    print("Step 2: Applying manifests...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=40,
        current_step="Applying Deployment manifest",
        applied_manifests=["configmap-app-config", "deployment-web"],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(1)
    
    # Step 3: Encounter error
    print("Step 3: Error encountered - invalid manifest!")
    await websocket_handler.send_error(
        deployment_id=deployment_id,
        error_message="Failed to apply Service manifest",
        error_details={
            "manifest": "service-web",
            "reason": "Invalid port configuration",
            "kubernetes_error": "Service 'web' is invalid: spec.ports[0].port: Invalid value"
        }
    )
    await asyncio.sleep(1)
    
    # Step 4: Rollback
    print("Step 4: Rolling back deployment...")
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=60,
        current_step="Rolling back deployment",
        applied_manifests=["configmap-app-config", "deployment-web"],
        timestamp=datetime.utcnow()
    )
    await websocket_handler.send_progress(deployment_id, update)
    await asyncio.sleep(1)
    
    # Step 5: Rollback complete
    print("Step 5: Rollback completed")
    await websocket_handler.send_completion(
        deployment_id=deployment_id,
        status=DeploymentStatus.ROLLED_BACK,
        message="Deployment failed and was rolled back",
        details={
            "error": "Invalid Service manifest",
            "rolled_back_manifests": ["deployment-web", "configmap-app-config"],
            "duration_seconds": 4
        }
    )
    
    print(f"\n=== Deployment {deployment_id} Rolled Back ===\n")


async def main():
    """
    Main function to demonstrate WebSocket handler usage.
    """
    print("\n" + "="*60)
    print("WebSocket Handler Usage Examples")
    print("="*60)
    
    print("\nNote: In a real application, clients would connect via WebSocket")
    print("to receive these updates in real-time. This example simulates")
    print("the server-side broadcasting of updates.\n")
    
    # Example 1: Successful deployment
    await simulate_deployment_with_websocket("deployment-success-001")
    
    # Wait a bit between examples
    await asyncio.sleep(2)
    
    # Example 2: Failed deployment with rollback
    await simulate_failed_deployment("deployment-failed-002")
    
    print("\n" + "="*60)
    print("Examples Complete")
    print("="*60 + "\n")
    
    print("Connection Statistics:")
    print(f"  Total connections: {websocket_handler.get_total_connections()}")
    print(f"  Active deployments: {len(websocket_handler.connections)}")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
