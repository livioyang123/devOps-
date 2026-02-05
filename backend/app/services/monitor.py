"""
Monitor Service for collecting metrics and logs from Kubernetes clusters.

This service integrates with Prometheus for metrics collection and Loki for log aggregation.
"""

import httpx
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime, timedelta
from app.config import settings
from app.schemas import (
    PodMetrics,
    ServiceMetrics,
    MetricsData,
    NetworkMetrics,
    TimeRange,
    LogEntry,
    LogFilters
)
import logging

logger = logging.getLogger(__name__)


class MonitorService:
    """
    Service for monitoring Kubernetes deployments.
    
    Integrates with:
    - Prometheus for metrics collection (CPU, memory, network, storage)
    - Loki for log aggregation and streaming
    """
    
    def __init__(
        self,
        prometheus_url: Optional[str] = None,
        loki_url: Optional[str] = None
    ):
        """
        Initialize MonitorService.
        
        Args:
            prometheus_url: Prometheus server URL (defaults to settings)
            loki_url: Loki server URL (defaults to settings)
        """
        self.prometheus_url = prometheus_url or settings.prometheus_url
        self.loki_url = loki_url or settings.loki_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client connections."""
        await self.client.aclose()
    
    async def get_pod_metrics(
        self,
        namespace: str,
        time_range: Optional[TimeRange] = None,
        pod_name: Optional[str] = None
    ) -> List[PodMetrics]:
        """
        Query Prometheus for pod CPU, memory, and network metrics.
        
        Args:
            namespace: Kubernetes namespace
            time_range: Optional time range for historical metrics
            pod_name: Optional specific pod name to filter
        
        Returns:
            List of PodMetrics with CPU, memory, and network data
        
        Raises:
            httpx.HTTPError: If Prometheus query fails
        """
        try:
            # Default to last 5 minutes if no time range specified
            if not time_range:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=5)
                time_range = TimeRange(start=start_time, end=end_time)
            
            # Build label selector
            label_selector = f'namespace="{namespace}"'
            if pod_name:
                label_selector += f',pod="{pod_name}"'
            
            # Collect all metrics
            cpu_metrics = await self._query_cpu_usage(label_selector, time_range)
            memory_metrics = await self._query_memory_usage(label_selector, time_range)
            network_metrics = await self._query_network_usage(label_selector, time_range)
            
            # Combine metrics by pod
            pod_metrics_map: Dict[str, Dict[str, Any]] = {}
            
            # Process CPU metrics
            for metric in cpu_metrics:
                pod = metric.get("metric", {}).get("pod")
                if pod:
                    if pod not in pod_metrics_map:
                        pod_metrics_map[pod] = {
                            "name": pod,
                            "namespace": namespace,
                            "cpu_usage": 0.0,
                            "memory_usage": 0.0,
                            "network": {"rx_bytes": 0.0, "tx_bytes": 0.0}
                        }
                    # Get the latest value
                    value = metric.get("value", [None, "0"])
                    pod_metrics_map[pod]["cpu_usage"] = float(value[1])
            
            # Process memory metrics
            for metric in memory_metrics:
                pod = metric.get("metric", {}).get("pod")
                if pod:
                    if pod not in pod_metrics_map:
                        pod_metrics_map[pod] = {
                            "name": pod,
                            "namespace": namespace,
                            "cpu_usage": 0.0,
                            "memory_usage": 0.0,
                            "network": {"rx_bytes": 0.0, "tx_bytes": 0.0}
                        }
                    value = metric.get("value", [None, "0"])
                    pod_metrics_map[pod]["memory_usage"] = float(value[1])
            
            # Process network metrics
            for metric_type, metrics in network_metrics.items():
                for metric in metrics:
                    pod = metric.get("metric", {}).get("pod")
                    if pod:
                        if pod not in pod_metrics_map:
                            pod_metrics_map[pod] = {
                                "name": pod,
                                "namespace": namespace,
                                "cpu_usage": 0.0,
                                "memory_usage": 0.0,
                                "network": {"rx_bytes": 0.0, "tx_bytes": 0.0}
                            }
                        value = metric.get("value", [None, "0"])
                        if metric_type == "rx":
                            pod_metrics_map[pod]["network"]["rx_bytes"] = float(value[1])
                        else:
                            pod_metrics_map[pod]["network"]["tx_bytes"] = float(value[1])
            
            # Convert to PodMetrics objects
            result = []
            timestamp = datetime.utcnow()
            for pod_data in pod_metrics_map.values():
                result.append(PodMetrics(
                    name=pod_data["name"],
                    namespace=pod_data["namespace"],
                    cpu_usage=pod_data["cpu_usage"],
                    memory_usage=pod_data["memory_usage"],
                    network=NetworkMetrics(
                        rx_bytes=pod_data["network"]["rx_bytes"],
                        tx_bytes=pod_data["network"]["tx_bytes"]
                    ),
                    timestamp=timestamp
                ))
            
            logger.info(f"Collected metrics for {len(result)} pods in namespace {namespace}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to collect pod metrics: {e}")
            raise
    
    async def _query_cpu_usage(
        self,
        label_selector: str,
        time_range: TimeRange
    ) -> List[Dict[str, Any]]:
        """
        Query Prometheus for CPU usage metrics.
        
        Uses: rate(container_cpu_usage_seconds_total[5m])
        
        Args:
            label_selector: Prometheus label selector
            time_range: Time range for query
        
        Returns:
            List of metric results
        """
        query = f'rate(container_cpu_usage_seconds_total{{{label_selector},container!=""}}[5m])'
        return await self._prometheus_query(query, time_range.end)
    
    async def _query_memory_usage(
        self,
        label_selector: str,
        time_range: TimeRange
    ) -> List[Dict[str, Any]]:
        """
        Query Prometheus for memory usage metrics.
        
        Uses: container_memory_usage_bytes
        
        Args:
            label_selector: Prometheus label selector
            time_range: Time range for query
        
        Returns:
            List of metric results
        """
        query = f'container_memory_usage_bytes{{{label_selector},container!=""}}'
        return await self._prometheus_query(query, time_range.end)
    
    async def _query_network_usage(
        self,
        label_selector: str,
        time_range: TimeRange
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query Prometheus for network usage metrics.
        
        Uses:
        - rate(container_network_receive_bytes_total[5m])
        - rate(container_network_transmit_bytes_total[5m])
        
        Args:
            label_selector: Prometheus label selector
            time_range: Time range for query
        
        Returns:
            Dict with 'rx' and 'tx' metric results
        """
        rx_query = f'rate(container_network_receive_bytes_total{{{label_selector}}}[5m])'
        tx_query = f'rate(container_network_transmit_bytes_total{{{label_selector}}}[5m])'
        
        rx_metrics = await self._prometheus_query(rx_query, time_range.end)
        tx_metrics = await self._prometheus_query(tx_query, time_range.end)
        
        return {
            "rx": rx_metrics,
            "tx": tx_metrics
        }
    
    async def _prometheus_query(
        self,
        query: str,
        timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Prometheus query.
        
        Args:
            query: PromQL query string
            timestamp: Optional timestamp for query (defaults to now)
        
        Returns:
            List of metric results
        
        Raises:
            httpx.HTTPError: If query fails
        """
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {"query": query}
            
            if timestamp:
                params["time"] = timestamp.isoformat()
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") != "success":
                raise ValueError(f"Prometheus query failed: {data.get('error')}")
            
            return data.get("data", {}).get("result", [])
            
        except httpx.HTTPError as e:
            logger.error(f"Prometheus query failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error executing Prometheus query: {e}")
            raise
    
    async def stream_logs(
        self,
        namespace: str,
        pod_name: Optional[str] = None,
        filters: Optional[LogFilters] = None,
        time_range: Optional[TimeRange] = None
    ) -> AsyncIterator[LogEntry]:
        """
        Stream logs from Loki with optional filtering.
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Optional specific pod name
            filters: Optional log filters
            time_range: Optional time range
        
        Yields:
            LogEntry objects
        
        Raises:
            httpx.HTTPError: If Loki query fails
        """
        try:
            # Build LogQL query
            logql_query = self._build_logql_query(namespace, pod_name, filters)
            
            # Set time range
            if not time_range:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=1)
                time_range = TimeRange(start=start_time, end=end_time)
            
            # Query Loki for logs
            logs = await self._query_loki_range(logql_query, time_range)
            
            # Parse and yield log entries
            for log in logs:
                try:
                    log_entry = self._parse_log_entry(log)
                    if log_entry:
                        yield log_entry
                except Exception as e:
                    logger.warning(f"Failed to parse log entry: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to stream logs: {e}")
            raise
    
    async def search_logs(
        self,
        query: str,
        namespace: str,
        time_range: Optional[TimeRange] = None
    ) -> List[LogEntry]:
        """
        Full-text search across logs.
        
        Args:
            query: Search query string
            namespace: Kubernetes namespace
            time_range: Optional time range
        
        Returns:
            List of matching log entries
        
        Raises:
            httpx.HTTPError: If Loki query fails
        """
        try:
            # Build LogQL query with search filter
            filters = LogFilters(search_query=query)
            logql_query = self._build_logql_query(namespace, None, filters)
            
            # Set time range
            if not time_range:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=1)
                time_range = TimeRange(start=start_time, end=end_time)
            
            # Query Loki for logs
            logs = await self._query_loki_range(logql_query, time_range)
            
            # Parse log entries
            result = []
            for log in logs:
                try:
                    log_entry = self._parse_log_entry(log)
                    if log_entry:
                        result.append(log_entry)
                except Exception as e:
                    logger.warning(f"Failed to parse log entry: {e}")
                    continue
            
            logger.info(f"Found {len(result)} log entries matching query '{query}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to search logs: {e}")
            raise
    
    def _build_logql_query(
        self,
        namespace: str,
        pod_name: Optional[str] = None,
        filters: Optional[LogFilters] = None
    ) -> str:
        """
        Build LogQL query string with filters.
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Optional specific pod name
            filters: Optional log filters
        
        Returns:
            LogQL query string
        """
        # Start with namespace selector
        selectors = [f'namespace="{namespace}"']
        
        # Add pod name filter
        if pod_name:
            selectors.append(f'pod="{pod_name}"')
        
        # Add filters from LogFilters object
        if filters:
            if filters.pod_name:
                selectors.append(f'pod="{filters.pod_name}"')
            if filters.container_name:
                selectors.append(f'container="{filters.container_name}"')
        
        # Build base query
        query = "{" + ",".join(selectors) + "}"
        
        # Add search filter if provided
        if filters and filters.search_query:
            # Use LogQL |= operator for case-insensitive search
            query += f' |= "{filters.search_query}"'
        
        # Add level filter if provided
        if filters and filters.level:
            query += f' | json | level="{filters.level}"'
        
        return query
    
    async def _query_loki_range(
        self,
        query: str,
        time_range: TimeRange
    ) -> List[Dict[str, Any]]:
        """
        Execute a Loki range query.
        
        Args:
            query: LogQL query string
            time_range: Time range for query
        
        Returns:
            List of log entries
        
        Raises:
            httpx.HTTPError: If query fails
        """
        try:
            url = f"{self.loki_url}/loki/api/v1/query_range"
            
            # Convert timestamps to nanoseconds (Loki format)
            start_ns = int(time_range.start.timestamp() * 1e9)
            end_ns = int(time_range.end.timestamp() * 1e9)
            
            params = {
                "query": query,
                "start": start_ns,
                "end": end_ns,
                "limit": 5000,  # Maximum number of entries to return
                "direction": "forward"  # Chronological order
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") != "success":
                raise ValueError(f"Loki query failed: {data.get('error')}")
            
            # Extract log entries from response
            result = []
            result_data = data.get("data", {}).get("result", [])
            
            for stream in result_data:
                values = stream.get("values", [])
                stream_labels = stream.get("stream", {})
                
                for value in values:
                    # Each value is [timestamp_ns, log_line]
                    result.append({
                        "timestamp": value[0],
                        "line": value[1],
                        "labels": stream_labels
                    })
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Loki query failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error executing Loki query: {e}")
            raise
    
    def _parse_log_entry(self, log_data: Dict[str, Any]) -> Optional[LogEntry]:
        """
        Parse Loki log entry into LogEntry object.
        
        Args:
            log_data: Raw log data from Loki
        
        Returns:
            LogEntry object or None if parsing fails
        """
        try:
            # Extract timestamp (convert from nanoseconds)
            timestamp_ns = int(log_data["timestamp"])
            timestamp = datetime.fromtimestamp(timestamp_ns / 1e9)
            
            # Extract labels
            labels = log_data.get("labels", {})
            pod_name = labels.get("pod", labels.get("pod_name", "unknown"))
            container_name = labels.get("container", labels.get("container_name", "unknown"))
            
            # Extract log message
            message = log_data["line"]
            
            # Try to extract log level from message or labels
            level = "info"
            if "level" in labels:
                level = labels["level"].lower()
            else:
                # Try to detect level from message
                message_lower = message.lower()
                if "error" in message_lower or "err" in message_lower:
                    level = "error"
                elif "warn" in message_lower:
                    level = "warning"
                elif "debug" in message_lower:
                    level = "debug"
            
            return LogEntry(
                timestamp=timestamp,
                pod_name=pod_name,
                container_name=container_name,
                message=message,
                level=level
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse log entry: {e}")
            return None


# Singleton instance
_monitor_service: Optional[MonitorService] = None


def get_monitor_service() -> MonitorService:
    """
    Get or create MonitorService singleton instance.
    
    Returns:
        MonitorService instance
    """
    global _monitor_service
    if _monitor_service is None:
        _monitor_service = MonitorService()
    return _monitor_service
