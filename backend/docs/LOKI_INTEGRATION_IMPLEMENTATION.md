# Loki Integration Implementation

## Overview

This document describes the implementation of Loki integration for log streaming and search in the MonitorService. The integration enables real-time log aggregation, filtering, and full-text search across Kubernetes pods.

## Implementation Details

### Components Added

#### 1. Log Streaming (`stream_logs`)

**Purpose:** Stream logs from Loki with optional filtering by pod, container, level, and search query.

**Method Signature:**
```python
async def stream_logs(
    self,
    namespace: str,
    pod_name: Optional[str] = None,
    filters: Optional[LogFilters] = None,
    time_range: Optional[TimeRange] = None
) -> AsyncIterator[LogEntry]
```

**Features:**
- Real-time log streaming from Loki
- Support for filtering by pod name, container name, log level, and search query
- Configurable time range (defaults to last hour)
- Yields `LogEntry` objects with parsed log data
- Handles malformed log entries gracefully

**Usage Example:**
```python
from app.services.monitor import MonitorService
from app.schemas import LogFilters, TimeRange
from datetime import datetime, timedelta

monitor = MonitorService()

# Stream all logs from namespace
async for log_entry in monitor.stream_logs(namespace="default"):
    print(f"{log_entry.timestamp} - {log_entry.pod_name}: {log_entry.message}")

# Stream with filters
filters = LogFilters(
    pod_name="my-app",
    level="error",
    search_query="exception"
)

async for log_entry in monitor.stream_logs(namespace="default", filters=filters):
    print(f"ERROR: {log_entry.message}")
```

#### 2. Log Search (`search_logs`)

**Purpose:** Perform full-text search across logs and return matching entries.

**Method Signature:**
```python
async def search_logs(
    self,
    query: str,
    namespace: str,
    time_range: Optional[TimeRange] = None
) -> List[LogEntry]
```

**Features:**
- Full-text search using LogQL
- Returns list of matching log entries
- Configurable time range (defaults to last hour)
- Supports up to 5000 log entries per query

**Usage Example:**
```python
# Search for error logs
error_logs = await monitor.search_logs(
    query="error",
    namespace="production",
    time_range=TimeRange(
        start=datetime.utcnow() - timedelta(hours=1),
        end=datetime.utcnow()
    )
)

print(f"Found {len(error_logs)} error logs")
for log in error_logs[:10]:
    print(f"{log.pod_name}: {log.message}")
```

#### 3. LogQL Query Builder (`_build_logql_query`)

**Purpose:** Build LogQL query strings with filters.

**Features:**
- Constructs LogQL queries with namespace, pod, and container selectors
- Adds search filters using LogQL `|=` operator
- Adds level filters using LogQL JSON parsing
- Supports complex filter combinations

**Query Examples:**
```python
# Basic query
{namespace="default"}

# With pod filter
{namespace="default",pod="my-app"}

# With search filter
{namespace="default"} |= "error"

# With level filter
{namespace="default"} | json | level="error"

# Combined filters
{namespace="default",pod="my-app",container="app"} |= "exception" | json | level="error"
```

#### 4. Loki Range Query (`_query_loki_range`)

**Purpose:** Execute Loki range queries and parse results.

**Features:**
- Queries Loki `/loki/api/v1/query_range` endpoint
- Converts timestamps to nanoseconds (Loki format)
- Supports up to 5000 log entries per query
- Returns logs in chronological order
- Handles HTTP errors and invalid responses

**Response Format:**
```json
{
  "status": "success",
  "data": {
    "result": [
      {
        "stream": {
          "pod": "my-app-pod",
          "container": "app",
          "namespace": "default"
        },
        "values": [
          ["1234567890000000000", "Log message 1"],
          ["1234567891000000000", "Log message 2"]
        ]
      }
    ]
  }
}
```

#### 5. Log Entry Parser (`_parse_log_entry`)

**Purpose:** Parse raw Loki log data into `LogEntry` objects.

**Features:**
- Converts nanosecond timestamps to Python datetime
- Extracts pod name and container name from labels
- Detects log level from labels or message content
- Handles missing labels gracefully (defaults to "unknown")
- Returns `None` for unparseable entries

**Log Level Detection:**
- Checks `level` label first
- Falls back to message content analysis:
  - "error" or "err" → level="error"
  - "warn" → level="warning"
  - "debug" → level="debug"
  - Default → level="info"

## Configuration

### Environment Variables

The Loki URL is configured via environment variable:

```bash
LOKI_URL=http://loki:3100
```

### Docker Compose

Loki is configured in `docker-compose.yml`:

```yaml
loki:
  image: grafana/loki:2.9.0
  container_name: devops-loki
  ports:
    - "3100:3100"
  volumes:
    - ./infra/loki/loki-config.yml:/etc/loki/local-config.yaml
  command: -config.file=/etc/loki/local-config.yaml
```

## Data Models

### LogEntry

```python
class LogEntry(BaseModel):
    timestamp: datetime
    pod_name: str
    container_name: str
    message: str
    level: str = "info"
```

### LogFilters

```python
class LogFilters(BaseModel):
    pod_name: Optional[str] = None
    container_name: Optional[str] = None
    level: Optional[str] = None
    search_query: Optional[str] = None
```

### TimeRange

```python
class TimeRange(BaseModel):
    start: datetime
    end: datetime
```

## Testing

### Unit Tests

All Loki integration functionality is covered by unit tests in `backend/tests/test_monitor_service.py`:

- `test_build_logql_query_basic` - Basic query construction
- `test_build_logql_query_with_pod_name` - Query with pod filter
- `test_build_logql_query_with_filters` - Query with multiple filters
- `test_parse_log_entry_success` - Successful log parsing
- `test_parse_log_entry_detects_level_from_message` - Level detection
- `test_parse_log_entry_handles_missing_labels` - Missing label handling
- `test_query_loki_range_success` - Successful Loki query
- `test_query_loki_range_failure` - Error handling
- `test_search_logs_success` - Log search functionality
- `test_search_logs_default_time_range` - Default time range
- `test_stream_logs_success` - Log streaming
- `test_stream_logs_with_filters` - Filtered streaming
- `test_stream_logs_handles_parse_errors` - Error handling

Run tests:
```bash
pytest backend/tests/test_monitor_service.py -v
```

### Example Usage

See `backend/tests/example_monitor_usage.py` for comprehensive examples:

- `example_stream_logs()` - Basic log streaming
- `example_stream_logs_with_filters()` - Filtered log streaming
- `example_search_logs()` - Log search
- `example_search_pod_specific_logs()` - Pod-specific search
- `example_analyze_error_logs()` - Error log analysis

Run examples:
```bash
python backend/tests/example_monitor_usage.py
```

## Requirements Validation

This implementation satisfies the following requirements:

### Requirement 9.1: Real-time Log Streaming
✅ The `stream_logs` method streams logs from all pods in real-time using Loki's query_range API.

### Requirement 9.3: Log Search Filtering
✅ The `search_logs` method filters logs using full-text search with LogQL.

### Requirement 9.4: Pod-Specific Filtering
✅ Both methods support filtering by specific pod name via the `pod_name` parameter and `LogFilters`.

### Requirement 9.5: Time-Based Filtering
✅ Both methods support time range filtering via the `time_range` parameter.

## Error Handling

The implementation includes comprehensive error handling:

1. **HTTP Errors:** Caught and logged with details
2. **Invalid Responses:** Validated status and error messages
3. **Parse Errors:** Malformed log entries are skipped with warnings
4. **Missing Labels:** Default values provided for missing pod/container names
5. **Connection Failures:** Propagated to caller with context

## Performance Considerations

1. **Query Limits:** Maximum 5000 log entries per query to prevent memory issues
2. **Async Operations:** All I/O operations are async for non-blocking execution
3. **Streaming:** Uses async generators to yield logs incrementally
4. **Connection Pooling:** Reuses httpx client for multiple requests

## Future Enhancements

Potential improvements for future iterations:

1. **Pagination:** Support for querying more than 5000 logs
2. **Live Tailing:** WebSocket-based live log tailing
3. **Log Aggregation:** Group logs by pod/container for analysis
4. **Advanced Filters:** Support for regex patterns and complex LogQL queries
5. **Caching:** Cache recent log queries for faster retrieval
6. **Compression:** Support for compressed log responses

## Related Files

- `backend/app/services/monitor.py` - Main implementation
- `backend/app/schemas.py` - Data models
- `backend/app/config.py` - Configuration
- `backend/tests/test_monitor_service.py` - Unit tests
- `backend/tests/example_monitor_usage.py` - Usage examples
- `docker-compose.yml` - Loki service configuration
- `infra/loki/loki-config.yml` - Loki configuration

## Task Completion

This implementation completes **Task 17.1: Implement Loki integration for log streaming** from the DevOps K8s Platform specification.

**Subtask Details:**
- ✅ Integrate Loki client library (using httpx)
- ✅ Implement stream_logs method for real-time log streaming
- ✅ Implement search_logs method for full-text search
- ✅ Support filtering by pod, time range, and search query
- ✅ Validates Requirements: 9.1, 9.3, 9.4, 9.5
