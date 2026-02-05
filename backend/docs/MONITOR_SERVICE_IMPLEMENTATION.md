# Monitor Service Implementation

## Overview

The MonitorService provides integration with Prometheus for collecting Kubernetes cluster metrics. It enables real-time monitoring of pod CPU, memory, and network usage across deployments.

## Implementation Details

### Task 16.1: Prometheus Integration

**Status:** ✅ Completed

**Components Implemented:**

1. **MonitorService Class** (`app/services/monitor.py`)
   - Prometheus client integration using httpx
   - Async HTTP client for non-blocking queries
   - Singleton pattern via `get_monitor_service()`

2. **Metrics Collection Methods:**
   - `get_pod_metrics()` - Main method for collecting all pod metrics
   - `_query_cpu_usage()` - CPU usage via `rate(container_cpu_usage_seconds_total[5m])`
   - `_query_memory_usage()` - Memory usage via `container_memory_usage_bytes`
   - `_query_network_usage()` - Network RX/TX via `rate(container_network_*_bytes_total[5m])`
   - `_prometheus_query()` - Generic Prometheus query executor

3. **Data Models** (`app/schemas.py`)
   - `TimeRange` - Time range specification for queries
   - `PodMetrics` - Complete pod metrics (CPU, memory, network)
   - `NetworkMetrics` - Network RX/TX bytes
   - `ServiceMetrics` - Service-level metrics aggregation
   - `MetricsData` - Complete metrics response
   - `MetricsRequest` - Metrics query request

4. **Configuration** (`app/config.py`)
   - `prometheus_url` - Prometheus server URL (default: http://prometheus:9090)
   - `loki_url` - Loki server URL (default: http://loki:3100)

## Features

### Prometheus Queries

The service uses the following PromQL queries:

**CPU Usage:**
```promql
rate(container_cpu_usage_seconds_total{namespace="default",container!=""}[5m])
```
Returns CPU usage rate in cores over the last 5 minutes.

**Memory Usage:**
```promql
container_memory_usage_bytes{namespace="default",container!=""}
```
Returns current memory usage in bytes.

**Network Receive:**
```promql
rate(container_network_receive_bytes_total{namespace="default"}[5m])
```
Returns network receive rate in bytes/second.

**Network Transmit:**
```promql
rate(container_network_transmit_bytes_total{namespace="default"}[5m])
```
Returns network transmit rate in bytes/second.

### Time Range Support

- Default: Last 5 minutes if no time range specified
- Custom: Specify start and end datetime for historical queries
- Queries use instant queries at the end timestamp

### Pod Filtering

- Collect metrics for all pods in a namespace
- Filter by specific pod name
- Automatic aggregation by pod name

### Error Handling

- HTTP errors from Prometheus are propagated
- Invalid query responses raise ValueError
- Connection failures raise httpx.HTTPError
- Graceful handling of missing metrics (defaults to 0.0)

## Usage Examples

### Basic Usage

```python
from app.services.monitor import get_monitor_service
from app.schemas import TimeRange
from datetime import datetime, timedelta

# Get service instance
monitor = get_monitor_service()

# Collect metrics for all pods
metrics = await monitor.get_pod_metrics(namespace="default")

# Display results
for pod in metrics:
    print(f"{pod.name}: CPU={pod.cpu_usage}, Memory={pod.memory_usage}")
```

### With Time Range

```python
# Define time range
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=1)
time_range = TimeRange(start=start_time, end=end_time)

# Collect historical metrics
metrics = await monitor.get_pod_metrics(
    namespace="production",
    time_range=time_range
)
```

### Specific Pod

```python
# Monitor specific pod
metrics = await monitor.get_pod_metrics(
    namespace="default",
    pod_name="my-app-pod-12345"
)
```

## Testing

### Unit Tests

Location: `backend/tests/test_monitor_service.py`

**Test Coverage:**
- ✅ Service initialization
- ✅ Singleton pattern
- ✅ Prometheus query execution
- ✅ CPU usage queries
- ✅ Memory usage queries
- ✅ Network usage queries
- ✅ Complete pod metrics collection
- ✅ Pod filtering
- ✅ Default time range
- ✅ Error handling
- ✅ Missing metrics handling

**Run Tests:**
```bash
pytest backend/tests/test_monitor_service.py -v
```

### Example Usage

Location: `backend/tests/example_monitor_usage.py`

Demonstrates:
- Collecting metrics for all pods
- Filtering by specific pod
- Historical metrics queries
- Monitoring deployments
- Resource usage alerts

**Run Examples:**
```bash
python backend/tests/example_monitor_usage.py
```

## Integration

### Docker Compose

Prometheus is configured in `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus:v2.47.0
  ports:
    - "9090:9090"
  volumes:
    - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
```

### Environment Variables

Set in backend service:
```yaml
environment:
  - PROMETHEUS_URL=http://prometheus:9090
  - LOKI_URL=http://loki:3100
```

## Requirements Validation

### Requirement 8.1: CPU Usage Metrics ✅
- Implemented via `_query_cpu_usage()` using `container_cpu_usage_seconds_total`

### Requirement 8.2: Memory Usage Metrics ✅
- Implemented via `_query_memory_usage()` using `container_memory_usage_bytes`

### Requirement 8.3: Network Traffic Metrics ✅
- Implemented via `_query_network_usage()` using `container_network_*_bytes_total`

### Requirement 8.4: Storage Usage Metrics ⏳
- Network metrics implemented (RX/TX)
- Storage metrics will be added in future enhancements

### Requirement 8.7: Time Range Filtering ✅
- Implemented via `TimeRange` parameter in `get_pod_metrics()`
- Supports custom start/end timestamps

## Future Enhancements

### Task 17: Log Aggregation (Loki Integration)
- `stream_logs()` - Real-time log streaming
- `search_logs()` - Full-text log search
- Log filtering by pod, container, level

### Task 18: Monitoring API Endpoints
- GET `/api/metrics/{deployment_id}` - Metrics endpoint
- GET `/api/logs/{deployment_id}` - Logs endpoint
- WebSocket streaming for real-time updates

### Task 19: Frontend Monitoring Dashboard
- Real-time charts with Recharts
- Log viewer component
- Automatic refresh
- Time range selection

## Architecture

```
┌─────────────────┐
│   Frontend      │
│  (Next.js)      │
└────────┬────────┘
         │ HTTP GET /api/metrics
         ▼
┌─────────────────┐
│   FastAPI       │
│   Backend       │
└────────┬────────┘
         │ get_pod_metrics()
         ▼
┌─────────────────┐
│ MonitorService  │
│  (Python)       │
└────────┬────────┘
         │ PromQL queries
         ▼
┌─────────────────┐
│  Prometheus     │
│   (Metrics)     │
└─────────────────┘
         ▲
         │ scrape metrics
         │
┌─────────────────┐
│  Kubernetes     │
│   Cluster       │
└─────────────────┘
```

## Performance Considerations

### Query Optimization
- Use instant queries instead of range queries for current metrics
- 5-minute rate windows for CPU and network metrics
- Efficient label selectors to reduce query scope

### Caching Strategy
- Consider caching metrics for 10-30 seconds
- Reduce Prometheus query load
- Balance freshness vs. performance

### Connection Pooling
- httpx.AsyncClient with connection pooling
- Reuse connections across queries
- Timeout set to 30 seconds

## Troubleshooting

### Prometheus Connection Failed
```
Error: httpx.HTTPError: Connection failed
```
**Solution:** Verify Prometheus is running and accessible at configured URL

### No Metrics Returned
```
Result: []
```
**Possible Causes:**
- Namespace doesn't exist
- No pods in namespace
- Prometheus not scraping metrics
- Label selectors too restrictive

### Invalid Query Response
```
Error: Prometheus query failed: <error message>
```
**Solution:** Check PromQL query syntax and metric names

## References

- [Prometheus Query API](https://prometheus.io/docs/prometheus/latest/querying/api/)
- [PromQL Documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Kubernetes Metrics](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- [Container Metrics](https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md)
