"""
Example usage of MonitorService for collecting Kubernetes metrics.

This demonstrates how to use the MonitorService to collect CPU, memory,
and network metrics from Prometheus.
"""

import asyncio
from datetime import datetime, timedelta
from app.services.monitor import MonitorService
from app.schemas import TimeRange


async def example_collect_metrics():
    """Example: Collect metrics for all pods in a namespace."""
    
    # Initialize MonitorService
    monitor = MonitorService(
        prometheus_url="http://localhost:9090",
        loki_url="http://localhost:3100"
    )
    
    try:
        # Define time range (last 5 minutes)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        time_range = TimeRange(start=start_time, end=end_time)
        
        # Collect metrics for all pods in default namespace
        print("Collecting metrics for all pods in 'default' namespace...")
        pod_metrics = await monitor.get_pod_metrics(
            namespace="default",
            time_range=time_range
        )
        
        # Display results
        print(f"\nFound {len(pod_metrics)} pods with metrics:\n")
        for pod in pod_metrics:
            print(f"Pod: {pod.name}")
            print(f"  CPU Usage: {pod.cpu_usage:.4f} cores")
            print(f"  Memory Usage: {pod.memory_usage / (1024**3):.2f} GB")
            print(f"  Network RX: {pod.network.rx_bytes / (1024**2):.2f} MB")
            print(f"  Network TX: {pod.network.tx_bytes / (1024**2):.2f} MB")
            print(f"  Timestamp: {pod.timestamp}")
            print()
        
    finally:
        await monitor.close()


async def example_collect_specific_pod_metrics():
    """Example: Collect metrics for a specific pod."""
    
    monitor = MonitorService()
    
    try:
        # Collect metrics for specific pod
        pod_name = "my-app-pod-12345"
        print(f"Collecting metrics for pod '{pod_name}'...")
        
        pod_metrics = await monitor.get_pod_metrics(
            namespace="default",
            pod_name=pod_name
        )
        
        if pod_metrics:
            pod = pod_metrics[0]
            print(f"\nMetrics for {pod.name}:")
            print(f"  CPU: {pod.cpu_usage:.4f} cores")
            print(f"  Memory: {pod.memory_usage / (1024**3):.2f} GB")
            print(f"  Network RX: {pod.network.rx_bytes / (1024**2):.2f} MB/s")
            print(f"  Network TX: {pod.network.tx_bytes / (1024**2):.2f} MB/s")
        else:
            print(f"No metrics found for pod '{pod_name}'")
        
    finally:
        await monitor.close()


async def example_collect_historical_metrics():
    """Example: Collect historical metrics over a custom time range."""
    
    monitor = MonitorService()
    
    try:
        # Define custom time range (last hour)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        time_range = TimeRange(start=start_time, end=end_time)
        
        print(f"Collecting metrics from {start_time} to {end_time}...")
        
        pod_metrics = await monitor.get_pod_metrics(
            namespace="production",
            time_range=time_range
        )
        
        # Calculate average CPU usage
        if pod_metrics:
            avg_cpu = sum(p.cpu_usage for p in pod_metrics) / len(pod_metrics)
            avg_memory = sum(p.memory_usage for p in pod_metrics) / len(pod_metrics)
            
            print(f"\nAverage metrics across {len(pod_metrics)} pods:")
            print(f"  Average CPU: {avg_cpu:.4f} cores")
            print(f"  Average Memory: {avg_memory / (1024**3):.2f} GB")
        
    finally:
        await monitor.close()


async def example_monitor_deployment():
    """Example: Monitor a specific deployment's pods."""
    
    monitor = MonitorService()
    
    try:
        deployment_namespace = "default"
        
        # In a real scenario, you would filter by deployment labels
        # For this example, we collect all pods
        pod_metrics = await monitor.get_pod_metrics(
            namespace=deployment_namespace
        )
        
        # Group by deployment (simplified - in reality use labels)
        print(f"Monitoring deployment in namespace '{deployment_namespace}':")
        print(f"Total pods: {len(pod_metrics)}")
        
        # Check for high resource usage
        high_cpu_pods = [p for p in pod_metrics if p.cpu_usage > 0.8]
        high_memory_pods = [p for p in pod_metrics if p.memory_usage > 2 * (1024**3)]
        
        if high_cpu_pods:
            print(f"\n⚠️  High CPU usage detected on {len(high_cpu_pods)} pods:")
            for pod in high_cpu_pods:
                print(f"  - {pod.name}: {pod.cpu_usage:.2f} cores")
        
        if high_memory_pods:
            print(f"\n⚠️  High memory usage detected on {len(high_memory_pods)} pods:")
            for pod in high_memory_pods:
                print(f"  - {pod.name}: {pod.memory_usage / (1024**3):.2f} GB")
        
        if not high_cpu_pods and not high_memory_pods:
            print("\n✅ All pods are running within normal resource limits")
        
    finally:
        await monitor.close()


async def example_stream_logs():
    """Example: Stream logs from all pods in a namespace."""
    
    monitor = MonitorService(
        prometheus_url="http://localhost:9090",
        loki_url="http://localhost:3100"
    )
    
    try:
        # Define time range (last 10 minutes)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=10)
        time_range = TimeRange(start=start_time, end=end_time)
        
        print("Streaming logs from 'default' namespace...")
        print("-" * 60)
        
        # Stream logs
        log_count = 0
        async for log_entry in monitor.stream_logs(
            namespace="default",
            time_range=time_range
        ):
            print(f"[{log_entry.timestamp}] [{log_entry.level.upper()}] {log_entry.pod_name}/{log_entry.container_name}")
            print(f"  {log_entry.message}")
            print()
            
            log_count += 1
            if log_count >= 10:  # Limit to first 10 logs for demo
                break
        
        print(f"Displayed {log_count} log entries")
        
    finally:
        await monitor.close()


async def example_stream_logs_with_filters():
    """Example: Stream logs with filters."""
    
    from app.schemas import LogFilters
    
    monitor = MonitorService()
    
    try:
        # Define filters
        filters = LogFilters(
            pod_name="my-app-pod",
            level="error",
            search_query="exception"
        )
        
        print("Streaming error logs containing 'exception' from 'my-app-pod'...")
        print("-" * 60)
        
        # Stream filtered logs
        async for log_entry in monitor.stream_logs(
            namespace="default",
            filters=filters
        ):
            print(f"[{log_entry.timestamp}] {log_entry.message}")
        
    finally:
        await monitor.close()


async def example_search_logs():
    """Example: Search logs for specific text."""
    
    monitor = MonitorService()
    
    try:
        # Define time range (last hour)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        time_range = TimeRange(start=start_time, end=end_time)
        
        # Search for error logs
        search_query = "error"
        print(f"Searching for logs containing '{search_query}'...")
        
        log_entries = await monitor.search_logs(
            query=search_query,
            namespace="default",
            time_range=time_range
        )
        
        print(f"\nFound {len(log_entries)} log entries:\n")
        
        # Display first 5 results
        for log_entry in log_entries[:5]:
            print(f"[{log_entry.timestamp}] {log_entry.pod_name}/{log_entry.container_name}")
            print(f"  Level: {log_entry.level}")
            print(f"  Message: {log_entry.message}")
            print()
        
        if len(log_entries) > 5:
            print(f"... and {len(log_entries) - 5} more entries")
        
    finally:
        await monitor.close()


async def example_search_pod_specific_logs():
    """Example: Search logs for a specific pod."""
    
    from app.schemas import LogFilters
    
    monitor = MonitorService()
    
    try:
        # Search for logs from specific pod
        pod_name = "my-app-pod-12345"
        search_query = "connection"
        
        print(f"Searching logs from pod '{pod_name}' for '{search_query}'...")
        
        filters = LogFilters(
            pod_name=pod_name,
            search_query=search_query
        )
        
        # Use stream_logs with filters
        log_entries = []
        async for log_entry in monitor.stream_logs(
            namespace="default",
            filters=filters
        ):
            log_entries.append(log_entry)
        
        print(f"\nFound {len(log_entries)} matching log entries")
        
        # Group by log level
        by_level = {}
        for entry in log_entries:
            by_level.setdefault(entry.level, []).append(entry)
        
        print("\nBreakdown by level:")
        for level, entries in sorted(by_level.items()):
            print(f"  {level}: {len(entries)} entries")
        
    finally:
        await monitor.close()


async def example_analyze_error_logs():
    """Example: Analyze error logs to identify issues."""
    
    monitor = MonitorService()
    
    try:
        # Search for error logs
        print("Analyzing error logs from the last hour...")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        time_range = TimeRange(start=start_time, end=end_time)
        
        error_logs = await monitor.search_logs(
            query="error",
            namespace="production",
            time_range=time_range
        )
        
        print(f"\nFound {len(error_logs)} error log entries")
        
        # Analyze error patterns
        error_patterns = {}
        for log in error_logs:
            # Extract error type (simplified)
            if "connection" in log.message.lower():
                error_patterns.setdefault("Connection Errors", []).append(log)
            elif "timeout" in log.message.lower():
                error_patterns.setdefault("Timeout Errors", []).append(log)
            elif "exception" in log.message.lower():
                error_patterns.setdefault("Exceptions", []).append(log)
            else:
                error_patterns.setdefault("Other Errors", []).append(log)
        
        print("\nError breakdown:")
        for pattern, logs in sorted(error_patterns.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {pattern}: {len(logs)} occurrences")
            
            # Show affected pods
            affected_pods = set(log.pod_name for log in logs)
            print(f"    Affected pods: {', '.join(list(affected_pods)[:3])}")
            if len(affected_pods) > 3:
                print(f"    ... and {len(affected_pods) - 3} more")
            print()
        
    finally:
        await monitor.close()


if __name__ == "__main__":
    print("=" * 60)
    print("MonitorService Usage Examples")
    print("=" * 60)
    print()
    
    print("Example 1: Collect metrics for all pods")
    print("-" * 60)
    asyncio.run(example_collect_metrics())
    
    print("\n" + "=" * 60)
    print("Example 2: Collect metrics for specific pod")
    print("-" * 60)
    asyncio.run(example_collect_specific_pod_metrics())
    
    print("\n" + "=" * 60)
    print("Example 3: Collect historical metrics")
    print("-" * 60)
    asyncio.run(example_collect_historical_metrics())
    
    print("\n" + "=" * 60)
    print("Example 4: Monitor deployment")
    print("-" * 60)
    asyncio.run(example_monitor_deployment())
    
    print("\n" + "=" * 60)
    print("Example 5: Stream logs")
    print("-" * 60)
    asyncio.run(example_stream_logs())
    
    print("\n" + "=" * 60)
    print("Example 6: Stream logs with filters")
    print("-" * 60)
    asyncio.run(example_stream_logs_with_filters())
    
    print("\n" + "=" * 60)
    print("Example 7: Search logs")
    print("-" * 60)
    asyncio.run(example_search_logs())
    
    print("\n" + "=" * 60)
    print("Example 8: Search pod-specific logs")
    print("-" * 60)
    asyncio.run(example_search_pod_specific_logs())
    
    print("\n" + "=" * 60)
    print("Example 9: Analyze error logs")
    print("-" * 60)
    asyncio.run(example_analyze_error_logs())
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
