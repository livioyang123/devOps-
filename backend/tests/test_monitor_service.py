"""
Unit tests for MonitorService
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.monitor import MonitorService, get_monitor_service
from app.schemas import TimeRange, PodMetrics, NetworkMetrics
import httpx


@pytest.fixture
def monitor_service():
    """Create MonitorService instance for testing."""
    service = MonitorService(
        prometheus_url="http://test-prometheus:9090",
        loki_url="http://test-loki:3100"
    )
    yield service


@pytest.fixture
def time_range():
    """Create a test time range."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=5)
    return TimeRange(start=start_time, end=end_time)


@pytest.mark.asyncio
async def test_monitor_service_initialization():
    """Test MonitorService initializes with correct URLs."""
    service = MonitorService(
        prometheus_url="http://custom-prometheus:9090",
        loki_url="http://custom-loki:3100"
    )
    
    assert service.prometheus_url == "http://custom-prometheus:9090"
    assert service.loki_url == "http://custom-loki:3100"
    assert service.client is not None
    
    await service.close()


@pytest.mark.asyncio
async def test_get_monitor_service_singleton():
    """Test get_monitor_service returns singleton instance."""
    service1 = get_monitor_service()
    service2 = get_monitor_service()
    
    assert service1 is service2


@pytest.mark.asyncio
async def test_prometheus_query_success(monitor_service):
    """Test successful Prometheus query execution."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "data": {
            "result": [
                {
                    "metric": {"pod": "test-pod"},
                    "value": [1234567890, "0.5"]
                }
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(monitor_service.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await monitor_service._prometheus_query("test_query")
        
        assert len(result) == 1
        assert result[0]["metric"]["pod"] == "test-pod"
        assert result[0]["value"][1] == "0.5"
        
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_prometheus_query_failure(monitor_service):
    """Test Prometheus query handles errors."""
    with patch.object(monitor_service.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")
        
        with pytest.raises(httpx.HTTPError):
            await monitor_service._prometheus_query("test_query")


@pytest.mark.asyncio
async def test_query_cpu_usage(monitor_service, time_range):
    """Test CPU usage query construction."""
    mock_result = [
        {
            "metric": {"pod": "test-pod", "namespace": "default"},
            "value": [1234567890, "0.25"]
        }
    ]
    
    with patch.object(monitor_service, '_prometheus_query', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_result
        
        result = await monitor_service._query_cpu_usage('namespace="default"', time_range)
        
        assert result == mock_result
        mock_query.assert_called_once()
        
        # Verify query format
        call_args = mock_query.call_args
        query = call_args[0][0]
        assert "rate(container_cpu_usage_seconds_total" in query
        assert 'namespace="default"' in query


@pytest.mark.asyncio
async def test_query_memory_usage(monitor_service, time_range):
    """Test memory usage query construction."""
    mock_result = [
        {
            "metric": {"pod": "test-pod", "namespace": "default"},
            "value": [1234567890, "1073741824"]  # 1GB
        }
    ]
    
    with patch.object(monitor_service, '_prometheus_query', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_result
        
        result = await monitor_service._query_memory_usage('namespace="default"', time_range)
        
        assert result == mock_result
        mock_query.assert_called_once()
        
        # Verify query format
        call_args = mock_query.call_args
        query = call_args[0][0]
        assert "container_memory_usage_bytes" in query
        assert 'namespace="default"' in query


@pytest.mark.asyncio
async def test_query_network_usage(monitor_service, time_range):
    """Test network usage query construction."""
    mock_rx_result = [
        {
            "metric": {"pod": "test-pod"},
            "value": [1234567890, "1000000"]
        }
    ]
    mock_tx_result = [
        {
            "metric": {"pod": "test-pod"},
            "value": [1234567890, "2000000"]
        }
    ]
    
    with patch.object(monitor_service, '_prometheus_query', new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = [mock_rx_result, mock_tx_result]
        
        result = await monitor_service._query_network_usage('namespace="default"', time_range)
        
        assert "rx" in result
        assert "tx" in result
        assert result["rx"] == mock_rx_result
        assert result["tx"] == mock_tx_result
        assert mock_query.call_count == 2


@pytest.mark.asyncio
async def test_get_pod_metrics_success(monitor_service, time_range):
    """Test successful pod metrics collection."""
    # Mock CPU metrics
    mock_cpu = [
        {
            "metric": {"pod": "test-pod-1", "namespace": "default"},
            "value": [1234567890, "0.5"]
        },
        {
            "metric": {"pod": "test-pod-2", "namespace": "default"},
            "value": [1234567890, "0.3"]
        }
    ]
    
    # Mock memory metrics
    mock_memory = [
        {
            "metric": {"pod": "test-pod-1", "namespace": "default"},
            "value": [1234567890, "1073741824"]  # 1GB
        },
        {
            "metric": {"pod": "test-pod-2", "namespace": "default"},
            "value": [1234567890, "536870912"]  # 512MB
        }
    ]
    
    # Mock network metrics
    mock_network = {
        "rx": [
            {
                "metric": {"pod": "test-pod-1"},
                "value": [1234567890, "1000000"]
            }
        ],
        "tx": [
            {
                "metric": {"pod": "test-pod-1"},
                "value": [1234567890, "2000000"]
            }
        ]
    }
    
    with patch.object(monitor_service, '_query_cpu_usage', new_callable=AsyncMock) as mock_cpu_query, \
         patch.object(monitor_service, '_query_memory_usage', new_callable=AsyncMock) as mock_mem_query, \
         patch.object(monitor_service, '_query_network_usage', new_callable=AsyncMock) as mock_net_query:
        
        mock_cpu_query.return_value = mock_cpu
        mock_mem_query.return_value = mock_memory
        mock_net_query.return_value = mock_network
        
        result = await monitor_service.get_pod_metrics("default", time_range)
        
        assert len(result) == 2
        assert all(isinstance(m, PodMetrics) for m in result)
        
        # Check first pod
        pod1 = next(m for m in result if m.name == "test-pod-1")
        assert pod1.namespace == "default"
        assert pod1.cpu_usage == 0.5
        assert pod1.memory_usage == 1073741824
        assert pod1.network.rx_bytes == 1000000
        assert pod1.network.tx_bytes == 2000000
        
        # Check second pod
        pod2 = next(m for m in result if m.name == "test-pod-2")
        assert pod2.cpu_usage == 0.3
        assert pod2.memory_usage == 536870912


@pytest.mark.asyncio
async def test_get_pod_metrics_with_pod_filter(monitor_service, time_range):
    """Test pod metrics collection with specific pod filter."""
    mock_cpu = [
        {
            "metric": {"pod": "test-pod-1", "namespace": "default"},
            "value": [1234567890, "0.5"]
        }
    ]
    
    with patch.object(monitor_service, '_query_cpu_usage', new_callable=AsyncMock) as mock_cpu_query, \
         patch.object(monitor_service, '_query_memory_usage', new_callable=AsyncMock) as mock_mem_query, \
         patch.object(monitor_service, '_query_network_usage', new_callable=AsyncMock) as mock_net_query:
        
        mock_cpu_query.return_value = mock_cpu
        mock_mem_query.return_value = []
        mock_net_query.return_value = {"rx": [], "tx": []}
        
        result = await monitor_service.get_pod_metrics(
            "default",
            time_range,
            pod_name="test-pod-1"
        )
        
        # Verify label selector includes pod name
        call_args = mock_cpu_query.call_args
        label_selector = call_args[0][0]
        assert 'pod="test-pod-1"' in label_selector


@pytest.mark.asyncio
async def test_get_pod_metrics_default_time_range(monitor_service):
    """Test pod metrics uses default time range when not provided."""
    with patch.object(monitor_service, '_query_cpu_usage', new_callable=AsyncMock) as mock_cpu_query, \
         patch.object(monitor_service, '_query_memory_usage', new_callable=AsyncMock) as mock_mem_query, \
         patch.object(monitor_service, '_query_network_usage', new_callable=AsyncMock) as mock_net_query:
        
        mock_cpu_query.return_value = []
        mock_mem_query.return_value = []
        mock_net_query.return_value = {"rx": [], "tx": []}
        
        result = await monitor_service.get_pod_metrics("default")
        
        # Should still call the query methods
        assert mock_cpu_query.called
        assert mock_mem_query.called
        assert mock_net_query.called


@pytest.mark.asyncio
async def test_build_logql_query_basic(monitor_service):
    """Test basic LogQL query construction."""
    query = monitor_service._build_logql_query("default")
    
    assert 'namespace="default"' in query
    assert query.startswith("{")


@pytest.mark.asyncio
async def test_build_logql_query_with_pod_name(monitor_service):
    """Test LogQL query with pod name filter."""
    query = monitor_service._build_logql_query("default", pod_name="test-pod")
    
    assert 'namespace="default"' in query
    assert 'pod="test-pod"' in query


@pytest.mark.asyncio
async def test_build_logql_query_with_filters(monitor_service):
    """Test LogQL query with LogFilters."""
    from app.schemas import LogFilters
    
    filters = LogFilters(
        pod_name="test-pod",
        container_name="app",
        level="error",
        search_query="exception"
    )
    
    query = monitor_service._build_logql_query("default", filters=filters)
    
    assert 'namespace="default"' in query
    assert 'pod="test-pod"' in query
    assert 'container="app"' in query
    assert '|= "exception"' in query
    assert 'level="error"' in query


@pytest.mark.asyncio
async def test_parse_log_entry_success(monitor_service):
    """Test successful log entry parsing."""
    log_data = {
        "timestamp": "1234567890000000000",  # nanoseconds
        "line": "2024-01-01 12:00:00 ERROR Something went wrong",
        "labels": {
            "pod": "test-pod",
            "container": "app",
            "level": "error"
        }
    }
    
    entry = monitor_service._parse_log_entry(log_data)
    
    assert entry is not None
    assert entry.pod_name == "test-pod"
    assert entry.container_name == "app"
    assert entry.level == "error"
    assert "Something went wrong" in entry.message


@pytest.mark.asyncio
async def test_parse_log_entry_detects_level_from_message(monitor_service):
    """Test log level detection from message content."""
    log_data = {
        "timestamp": "1234567890000000000",
        "line": "ERROR: Connection failed",
        "labels": {
            "pod": "test-pod",
            "container": "app"
        }
    }
    
    entry = monitor_service._parse_log_entry(log_data)
    
    assert entry is not None
    assert entry.level == "error"


@pytest.mark.asyncio
async def test_parse_log_entry_handles_missing_labels(monitor_service):
    """Test log entry parsing with missing labels."""
    log_data = {
        "timestamp": "1234567890000000000",
        "line": "Test log message",
        "labels": {}
    }
    
    entry = monitor_service._parse_log_entry(log_data)
    
    assert entry is not None
    assert entry.pod_name == "unknown"
    assert entry.container_name == "unknown"
    assert entry.level == "info"


@pytest.mark.asyncio
async def test_query_loki_range_success(monitor_service, time_range):
    """Test successful Loki range query."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "data": {
            "result": [
                {
                    "stream": {
                        "pod": "test-pod",
                        "container": "app"
                    },
                    "values": [
                        ["1234567890000000000", "Log line 1"],
                        ["1234567891000000000", "Log line 2"]
                    ]
                }
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(monitor_service.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await monitor_service._query_loki_range("{namespace=\"default\"}", time_range)
        
        assert len(result) == 2
        assert result[0]["line"] == "Log line 1"
        assert result[1]["line"] == "Log line 2"
        assert result[0]["labels"]["pod"] == "test-pod"
        
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_query_loki_range_failure(monitor_service, time_range):
    """Test Loki range query handles errors."""
    with patch.object(monitor_service.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")
        
        with pytest.raises(httpx.HTTPError):
            await monitor_service._query_loki_range("{namespace=\"default\"}", time_range)


@pytest.mark.asyncio
async def test_search_logs_success(monitor_service, time_range):
    """Test successful log search."""
    mock_logs = [
        {
            "timestamp": "1234567890000000000",
            "line": "ERROR: Connection failed",
            "labels": {"pod": "test-pod", "container": "app"}
        },
        {
            "timestamp": "1234567891000000000",
            "line": "ERROR: Retry failed",
            "labels": {"pod": "test-pod", "container": "app"}
        }
    ]
    
    with patch.object(monitor_service, '_query_loki_range', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_logs
        
        result = await monitor_service.search_logs("ERROR", "default", time_range)
        
        assert len(result) == 2
        assert all(entry.pod_name == "test-pod" for entry in result)
        assert all("failed" in entry.message.lower() for entry in result)


@pytest.mark.asyncio
async def test_search_logs_default_time_range(monitor_service):
    """Test search_logs uses default time range when not provided."""
    with patch.object(monitor_service, '_query_loki_range', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = []
        
        result = await monitor_service.search_logs("error", "default")
        
        assert mock_query.called
        # Verify time range was created
        call_args = mock_query.call_args
        time_range_arg = call_args[0][1]
        assert isinstance(time_range_arg, TimeRange)


@pytest.mark.asyncio
async def test_stream_logs_success(monitor_service, time_range):
    """Test successful log streaming."""
    mock_logs = [
        {
            "timestamp": "1234567890000000000",
            "line": "Log line 1",
            "labels": {"pod": "test-pod", "container": "app"}
        },
        {
            "timestamp": "1234567891000000000",
            "line": "Log line 2",
            "labels": {"pod": "test-pod", "container": "app"}
        }
    ]
    
    with patch.object(monitor_service, '_query_loki_range', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_logs
        
        entries = []
        async for entry in monitor_service.stream_logs("default", time_range=time_range):
            entries.append(entry)
        
        assert len(entries) == 2
        assert entries[0].message == "Log line 1"
        assert entries[1].message == "Log line 2"


@pytest.mark.asyncio
async def test_stream_logs_with_filters(monitor_service, time_range):
    """Test log streaming with filters."""
    from app.schemas import LogFilters
    
    filters = LogFilters(
        pod_name="test-pod",
        search_query="error"
    )
    
    with patch.object(monitor_service, '_query_loki_range', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = []
        
        entries = []
        async for entry in monitor_service.stream_logs("default", filters=filters, time_range=time_range):
            entries.append(entry)
        
        # Verify query was built with filters
        call_args = mock_query.call_args
        query = call_args[0][0]
        assert 'pod="test-pod"' in query
        assert '|= "error"' in query


@pytest.mark.asyncio
async def test_stream_logs_handles_parse_errors(monitor_service, time_range):
    """Test log streaming handles malformed log entries."""
    mock_logs = [
        {
            "timestamp": "1234567890000000000",
            "line": "Valid log",
            "labels": {"pod": "test-pod", "container": "app"}
        },
        {
            # Missing timestamp - will fail to parse
            "line": "Invalid log",
            "labels": {"pod": "test-pod"}
        },
        {
            "timestamp": "1234567891000000000",
            "line": "Another valid log",
            "labels": {"pod": "test-pod", "container": "app"}
        }
    ]
    
    with patch.object(monitor_service, '_query_loki_range', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_logs
        
        entries = []
        async for entry in monitor_service.stream_logs("default", time_range=time_range):
            entries.append(entry)
        
        # Should only get valid entries
        assert len(entries) == 2
        assert entries[0].message == "Valid log"
        assert entries[1].message == "Another valid log"


@pytest.mark.asyncio
async def test_get_pod_metrics_handles_missing_metrics(monitor_service, time_range):
    """Test pod metrics handles pods with partial metrics."""
    # Pod 1 has all metrics, Pod 2 only has CPU
    mock_cpu = [
        {
            "metric": {"pod": "test-pod-1", "namespace": "default"},
            "value": [1234567890, "0.5"]
        },
        {
            "metric": {"pod": "test-pod-2", "namespace": "default"},
            "value": [1234567890, "0.3"]
        }
    ]
    
    mock_memory = [
        {
            "metric": {"pod": "test-pod-1", "namespace": "default"},
            "value": [1234567890, "1073741824"]
        }
    ]
    
    mock_network = {
        "rx": [],
        "tx": []
    }
    
    with patch.object(monitor_service, '_query_cpu_usage', new_callable=AsyncMock) as mock_cpu_query, \
         patch.object(monitor_service, '_query_memory_usage', new_callable=AsyncMock) as mock_mem_query, \
         patch.object(monitor_service, '_query_network_usage', new_callable=AsyncMock) as mock_net_query:
        
        mock_cpu_query.return_value = mock_cpu
        mock_mem_query.return_value = mock_memory
        mock_net_query.return_value = mock_network
        
        result = await monitor_service.get_pod_metrics("default", time_range)
        
        assert len(result) == 2
        
        # Pod 2 should have default values for missing metrics
        pod2 = next(m for m in result if m.name == "test-pod-2")
        assert pod2.cpu_usage == 0.3
        assert pod2.memory_usage == 0.0  # Default value
        assert pod2.network.rx_bytes == 0.0
        assert pod2.network.tx_bytes == 0.0
