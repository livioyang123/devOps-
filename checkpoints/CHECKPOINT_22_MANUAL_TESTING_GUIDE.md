# Checkpoint 22: Manual Testing Guide

This guide provides step-by-step instructions for manually testing the monitoring and analysis features.

## Prerequisites

1. **Infrastructure Running:**
   ```bash
   docker-compose up -d
   ```

2. **Backend Running:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

3. **Frontend Running:**
   ```bash
   cd frontend
   npm run dev
   ```

4. **Kubernetes Cluster:**
   - Local: `minikube start` or `kind create cluster`
   - Ensure kubectl is configured

## Test 1: Metrics Collection and Visualization

### Setup
1. Deploy a sample application to your Kubernetes cluster
2. Wait 2-3 minutes for metrics to be collected

### Testing Steps

1. **Navigate to Monitoring Dashboard:**
   - Open browser: `http://localhost:3000/monitor`
   - You should see the monitoring dashboard

2. **Verify Metrics Display:**
   - Check that CPU usage charts are displayed
   - Check that memory usage charts are displayed
   - Check that network traffic charts are displayed
   - Verify metrics are organized by pod and service

3. **Test Time Range Selection:**
   - Select "Last 5 minutes" from time range dropdown
   - Verify charts update with new data
   - Try "Last 1 hour" and verify historical data loads

4. **Test Auto-Refresh:**
   - Watch the dashboard for 30 seconds
   - Verify metrics update automatically
   - Check that timestamps are current

### Expected Results
- ✅ All metric types (CPU, memory, network) are displayed
- ✅ Charts render correctly with data points
- ✅ Time range selection works
- ✅ Auto-refresh updates data every 30 seconds

## Test 2: Log Streaming

### Testing Steps

1. **Navigate to Log Viewer:**
   - On monitoring dashboard, scroll to "Logs" section
   - Or navigate to dedicated log viewer

2. **Verify Log Display:**
   - Check that logs are displayed in scrollable view
   - Verify timestamps are shown for each log entry
   - Verify pod names and container names are displayed
   - Check that log levels (INFO, ERROR, WARNING) are shown

3. **Test Real-Time Streaming:**
   - Generate new logs in your application (make API calls, etc.)
   - Verify new logs appear automatically
   - Check that scroll position is preserved when new logs arrive

### Expected Results
- ✅ Logs stream in real-time
- ✅ All log fields are displayed correctly
- ✅ Scroll position is preserved
- ✅ Timestamps are accurate

## Test 3: Log Filtering

### Testing Steps

1. **Test Search Filtering:**
   - Enter "error" in the search box
   - Verify only logs containing "error" are displayed
   - Clear search and verify all logs return

2. **Test Pod Filtering:**
   - Select a specific pod from the pod dropdown
   - Verify only logs from that pod are displayed
   - Select "All Pods" and verify all logs return

3. **Test Time Range Filtering:**
   - Select "Last 5 minutes" from time range dropdown
   - Verify only recent logs are displayed
   - Select "Last 1 hour" and verify more logs appear

4. **Test Log Level Filtering:**
   - Select "ERROR" from level dropdown
   - Verify only error logs are displayed
   - Select "All Levels" and verify all logs return

5. **Test Combined Filters:**
   - Apply multiple filters simultaneously
   - Example: Pod = "web-pod-1" + Level = "ERROR" + Search = "timeout"
   - Verify results match all filter criteria

### Expected Results
- ✅ Search filtering works correctly
- ✅ Pod filtering works correctly
- ✅ Time range filtering works correctly
- ✅ Log level filtering works correctly
- ✅ Multiple filters can be combined

## Test 4: AI Log Analysis

### Setup
Ensure you have an LLM provider configured:
- **Local:** Ollama running on `http://localhost:11434`
- **Cloud:** OpenAI, Anthropic, or Google AI with valid API key

### Testing Steps

1. **Trigger Analysis:**
   - Click "Analyze Logs" button on log viewer
   - Wait for analysis to complete (10-30 seconds)

2. **Verify Analysis Display:**
   - Check that analysis summary is displayed
   - Verify severity level is shown (Critical, Warning, Info)
   - Check that detected anomalies are listed
   - Verify common errors are identified
   - Check that recommendations are provided

3. **Test with Different Log Scenarios:**
   
   **Scenario A: Normal Logs**
   - Filter to show only INFO logs
   - Run analysis
   - Verify analysis indicates healthy state
   
   **Scenario B: Error Logs**
   - Filter to show ERROR logs
   - Run analysis
   - Verify analysis identifies issues and provides recommendations
   
   **Scenario C: Mixed Logs**
   - Show all logs (INFO, WARNING, ERROR)
   - Run analysis
   - Verify analysis provides comprehensive summary

### Expected Results
- ✅ Analysis completes successfully
- ✅ Summary is clear and actionable
- ✅ Anomalies are detected correctly
- ✅ Recommendations are relevant
- ✅ Severity levels are appropriate

## Test 5: Kubernetes Error Detection

### Setup
Create pods with intentional errors to test detection:

```bash
# Create pod with memory limit that will OOMKill
kubectl run oom-test --image=polinux/stress --restart=Never -- stress --vm 1 --vm-bytes 512M

# Create pod with invalid image (ImagePullBackOff)
kubectl run image-test --image=invalid/nonexistent:latest

# Create pod that crashes (CrashLoopBackOff)
kubectl run crash-test --image=busybox --restart=Always -- sh -c "exit 1"
```

### Testing Steps

1. **Wait for Errors:**
   - Wait 2-3 minutes for errors to occur
   - Check pod status: `kubectl get pods`

2. **View Logs:**
   - Navigate to log viewer
   - Filter to show ERROR level logs

3. **Verify Error Detection:**
   - Check for "OOMKilled" in logs
   - Check for "ImagePullBackOff" in logs
   - Check for "CrashLoopBackOff" in logs

4. **Run AI Analysis:**
   - Click "Analyze Logs" button
   - Wait for analysis to complete

5. **Verify Error Identification:**
   - Check that analysis identifies OOMKilled error
   - Check that analysis identifies ImagePullBackOff error
   - Check that analysis identifies CrashLoopBackOff error
   - Verify recommendations are provided for each error type

### Expected Results
- ✅ OOMKilled errors are detected
- ✅ ImagePullBackOff errors are detected
- ✅ CrashLoopBackOff errors are detected
- ✅ AI analysis identifies all error types
- ✅ Recommendations are specific to each error type

### Cleanup
```bash
kubectl delete pod oom-test image-test crash-test
```

## Common Issues and Solutions

### Issue: No metrics displayed
**Solution:**
- Verify Prometheus is running: `curl http://localhost:9090`
- Check that Kubernetes cluster has metrics-server installed
- Verify pods are running: `kubectl get pods -A`

### Issue: No logs displayed
**Solution:**
- Verify Loki is running: `curl http://localhost:3100/ready`
- Check Loki configuration in docker-compose.yml
- Verify pods are generating logs: `kubectl logs <pod-name>`

### Issue: AI analysis fails
**Solution:**
- Verify LLM provider is running (Ollama: `curl http://localhost:11434/api/tags`)
- Check API keys are configured correctly
- Verify network connectivity to LLM provider
- Check backend logs for error messages

### Issue: Filters not working
**Solution:**
- Clear browser cache and reload
- Check browser console for JavaScript errors
- Verify API endpoints are responding: `curl http://localhost:8000/api/logs/<deployment-id>`

## Success Criteria

All tests pass when:
- ✅ Metrics are collected and displayed correctly
- ✅ Logs stream in real-time
- ✅ All filtering mechanisms work
- ✅ AI analysis provides meaningful insights
- ✅ Kubernetes errors are detected and categorized
- ✅ Recommendations are actionable and relevant

## Next Steps

After successful manual testing:
1. Document any issues found
2. Proceed to Task 23: Alert Service implementation
3. Consider performance testing with high log volumes
4. Test with production-like workloads

---

**Note:** This guide assumes you have completed Tasks 16-21. If any features are missing, complete those tasks first.
