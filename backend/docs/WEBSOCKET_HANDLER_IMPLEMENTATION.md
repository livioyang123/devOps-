# WebSocket Handler Implementation

## Overview

The WebSocket Handler provides real-time bidirectional communication between the backend and frontend for deployment progress updates. This implementation satisfies Requirements 6.3, 6.4, and 7.2 from the DevOps K8s Platform specification.

## Architecture

### Components

1. **WebSocketHandler Service** (`app/services/websocket_handler.py`)
   - Manages WebSocket connections per deployment
   - Broadcasts progress updates to all connected clients
   - Handles connection lifecycle (connect, disconnect)
   - Provides error and completion notifications

2. **WebSocket Router** (`app/routers/websocket.py`)
   - Exposes WebSocket endpoint `/ws/deployment/{deployment_id}`
   - Handles WebSocket connection establishment
   - Maintains connection alive with ping/pong
   - Provides status endpoint for monitoring

3. **Integration with Main App** (`app/main.py`)
   - WebSocket router included in FastAPI application
   - Available alongside REST API endpoints

## Features

### Connection Management

The handler maintains a registry of active WebSocket connections organized by deployment ID:

```python
connections: Dict[str, Set[WebSocket]] = {}
```

This allows:
- Multiple clients to connect to the same deployment
- Efficient broadcasting to all interested clients
- Automatic cleanup of disconnected clients

### Message Types

The WebSocket handler sends four types of messages to clients:

#### 1. Connection Established
Sent immediately after successful connection:
```json
{
  "type": "connection_established",
  "deployment_id": "uuid",
  "timestamp": "2024-01-01T12:00:00",
  "message": "WebSocket connection established successfully"
}
```

#### 2. Progress Update
Sent during deployment operations:
```json
{
  "type": "progress_update",
  "deployment_id": "uuid",
  "status": "in_progress",
  "progress": 50,
  "current_step": "Applying Service manifest",
  "applied_manifests": ["deployment-web", "service-web"],
  "timestamp": "2024-01-01T12:00:00"
}
```

#### 3. Error
Sent when deployment encounters an error:
```json
{
  "type": "error",
  "deployment_id": "uuid",
  "error": "Failed to apply manifest",
  "details": {
    "manifest": "service-web",
    "reason": "Invalid configuration"
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

#### 4. Completion
Sent when deployment completes (success, failure, or rollback):
```json
{
  "type": "completion",
  "deployment_id": "uuid",
  "status": "completed",
  "message": "Deployment completed successfully",
  "details": {
    "pods_healthy": 3,
    "services_created": 2
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

## Usage

### Server-Side (Backend)

#### Importing the Handler

```python
from app.services.websocket_handler import websocket_handler
from app.schemas import ProgressUpdate, DeploymentStatus
```

#### Sending Progress Updates

```python
# Create progress update
update = ProgressUpdate(
    deployment_id="deployment-123",
    status=DeploymentStatus.IN_PROGRESS,
    progress=50,
    current_step="Applying Service manifest",
    applied_manifests=["deployment-web"],
    timestamp=datetime.utcnow()
)

# Broadcast to all connected clients
await websocket_handler.send_progress("deployment-123", update)
```

#### Sending Error Messages

```python
await websocket_handler.send_error(
    deployment_id="deployment-123",
    error_message="Failed to apply manifest",
    error_details={"reason": "Invalid configuration"}
)
```

#### Sending Completion Messages

```python
await websocket_handler.send_completion(
    deployment_id="deployment-123",
    status=DeploymentStatus.COMPLETED,
    message="Deployment completed successfully",
    details={"pods_healthy": 3}
)
```

### Client-Side (Frontend)

#### Connecting to WebSocket

```typescript
const deploymentId = "deployment-123";
const ws = new WebSocket(`ws://localhost:8000/ws/deployment/${deploymentId}`);

ws.onopen = () => {
  console.log("WebSocket connected");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case "connection_established":
      console.log("Connection confirmed:", data.message);
      break;
      
    case "progress_update":
      updateProgressBar(data.progress);
      updateCurrentStep(data.current_step);
      updateAppliedManifests(data.applied_manifests);
      break;
      
    case "error":
      displayError(data.error, data.details);
      break;
      
    case "completion":
      displayFinalStatus(data.status, data.message, data.details);
      break;
  }
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = () => {
  console.log("WebSocket disconnected");
};
```

#### Implementing Reconnection Logic

```typescript
class DeploymentWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  connect(deploymentId: string) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/deployment/${deploymentId}`);
    
    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = Math.pow(2, this.reconnectAttempts) * 1000; // Exponential backoff
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect(deploymentId);
        }, delay);
      }
    };
    
    this.ws.onopen = () => {
      this.reconnectAttempts = 0; // Reset on successful connection
    };
  }
}
```

## Error Handling

### Connection Failures

The handler gracefully handles connection failures:

1. **During Send**: If a WebSocket fails during message send, it's automatically removed from the connection registry
2. **Disconnection**: Clients can disconnect at any time; the handler cleans up resources
3. **No Connections**: If no clients are connected, messages are logged but don't cause errors

### Failed Connections Cleanup

```python
# Track failed connections
failed_connections = set()

# Broadcast to all connections
for websocket in connections:
    try:
        await websocket.send_json(message)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        failed_connections.add(websocket)

# Clean up failed connections
for websocket in failed_connections:
    await self.disconnect(deployment_id, websocket)
```

## Monitoring

### Connection Statistics

Get real-time statistics about active connections:

```bash
curl http://localhost:8000/ws/status
```

Response:
```json
{
  "status": "operational",
  "total_connections": 5,
  "active_deployments": 2,
  "deployments": {
    "deployment-123": 3,
    "deployment-456": 2
  }
}
```

### Logging

The handler logs important events:

- Connection establishment
- Disconnection
- Message broadcasting
- Errors during send operations

Example logs:
```
INFO: WebSocket connected for deployment deployment-123. Total connections: 1
INFO: Progress update sent to WebSocket for deployment deployment-123: in_progress - 50%
INFO: WebSocket disconnected for deployment deployment-123. Remaining connections: 0
```

## Testing

### Unit Tests

Located in `backend/tests/test_websocket_handler.py`:

- Connection registration
- Multiple connections per deployment
- Disconnection and cleanup
- Progress broadcasting
- Error handling for failed connections
- Error and completion messages

Run tests:
```bash
pytest backend/tests/test_websocket_handler.py -v
```

### Integration Tests

Located in `backend/tests/test_websocket_endpoint.py`:

- WebSocket endpoint connection
- Ping/pong functionality
- Receiving progress updates
- Receiving error messages
- Receiving completion messages
- Multiple concurrent connections

Run tests:
```bash
pytest backend/tests/test_websocket_endpoint.py -v
```

### Example Usage

See `backend/tests/example_websocket_usage.py` for complete examples of:

- Successful deployment with progress updates
- Failed deployment with rollback
- Error handling

Run example:
```bash
python backend/tests/example_websocket_usage.py
```

## Performance Considerations

### Scalability

The current implementation stores connections in memory, which works well for:
- Single-server deployments
- Moderate number of concurrent deployments (< 1000)
- Multiple clients per deployment (< 100)

For larger scale deployments, consider:
- Redis Pub/Sub for multi-server broadcasting
- Connection pooling and limits
- Message queuing for reliability

### Memory Management

The handler automatically cleans up:
- Disconnected WebSocket connections
- Empty deployment connection sets
- Failed connections during broadcast

### Concurrent Connections

The handler supports multiple concurrent connections per deployment without blocking:
- Async/await for non-blocking I/O
- Set-based connection storage for efficient lookup
- Automatic cleanup of failed connections

## Requirements Validation

### Requirement 6.3: WebSocket Connection Management
✅ Implemented in `WebSocketHandler.connect()` and `WebSocketHandler.disconnect()`
- Accepts WebSocket connections
- Maintains connection registry
- Cleans up on disconnect

### Requirement 6.4: Progress Broadcasting
✅ Implemented in `WebSocketHandler.send_progress()`
- Broadcasts progress updates to all connected clients
- Includes deployment status, progress percentage, and current step
- Handles failed connections gracefully

### Requirement 7.2: Real-Time Updates
✅ Implemented via WebSocket endpoint `/ws/deployment/{deployment_id}`
- Clients receive updates without polling
- Updates sent immediately as deployment progresses
- Supports multiple message types (progress, error, completion)

## Future Enhancements

1. **Authentication**: Add token-based authentication for WebSocket connections
2. **Rate Limiting**: Implement rate limiting for message broadcasting
3. **Message Persistence**: Store messages in Redis for clients that reconnect
4. **Compression**: Enable WebSocket compression for large messages
5. **Metrics**: Add Prometheus metrics for connection counts and message rates
6. **Health Checks**: Implement periodic ping/pong for connection health

## Related Documentation

- [Deployer Service Implementation](./DEPLOYER_SERVICE_IMPLEMENTATION.md)
- [Task 11 Completion Summary](./TASK_11_COMPLETION_SUMMARY.md)
- [Requirements Document](../../.kiro/specs/devops-k8s-platform/requirements.md)
- [Design Document](../../.kiro/specs/devops-k8s-platform/design.md)
