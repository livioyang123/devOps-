# AI Analyzer Service Implementation

## Overview

The AI Analyzer Service provides intelligent log analysis for Kubernetes deployments using Large Language Models (LLMs). It detects anomalies, identifies common Kubernetes errors, and provides actionable recommendations to help operators quickly understand and resolve issues.

**Implementation Date:** February 5, 2026  
**Requirements:** 10.1, 10.2, 10.3, 10.4, 10.6  
**Tasks:** 20.1, 20.2

## Architecture

### Components

1. **AIAnalyzerService** (`backend/app/services/ai_analyzer.py`)
   - Core service for log analysis
   - Pattern-based error detection
   - LLM-powered anomaly detection
   - Recommendation generation

2. **API Endpoint** (`backend/app/routers/monitor.py`)
   - POST `/api/analyze-logs` - Analyze logs for a deployment

3. **Data Models** (`backend/app/schemas.py`)
   - `AnalysisRequest` - Request parameters
   - `AnalysisResult` - Analysis results
   - `KubernetesError` - Detected errors
   - `Anomaly` - Detected anomalies

## Features

### 1. Common Error Detection

The service uses pattern matching to detect common Kubernetes errors:

- **OOMKilled** - Out of memory errors
- **CrashLoopBackOff** - Container restart failures
- **ImagePullBackOff** - Image pull failures
- **PodEvicted** - Resource pressure evictions
- **ContainerCreating** - Container creation timeouts
- **NetworkError** - Network connectivity issues
- **VolumeMount** - Volume mounting failures
- **ConfigError** - Configuration errors

### 2. LLM-Powered Analysis

The service sends logs to an LLM for intelligent analysis:

- Anomaly detection across log patterns
- Severity classification (critical, warning, info, normal)
- Contextual understanding of issues
- Correlation of related problems

### 3. Actionable Recommendations

Based on detected errors, the service generates specific recommendations:

- Memory limit adjustments for OOMKilled errors
- Configuration fixes for CrashLoopBackOff
- Registry credential checks for ImagePullBackOff
- Network troubleshooting for connectivity issues
- Resource allocation guidance for evictions

## API Usage

### Analyze Logs Endpoint

**Endpoint:** `POST /api/analyze-logs`

**Request Body:**
```json
{
  "deployment_id": "uuid",
  "namespace": "default",
  "time_range": {
    "start": "2026-02-05T10:00:00Z",
    "end": "2026-02-05T11:00:00Z"
  },
  "model": "gpt-4"
}
```

**Response:**
```json
{
  "summary": "Multiple critical errors detected including OOMKilled and CrashLoopBackOff...",
  "severity": "critical",
  "common_errors": [
    {
      "error_type": "OOMKilled",
      "pod_name": "web-app-pod-1",
      "message": "OOMKilled: Container exceeded memory limit",
      "timestamp": "2026-02-05T10:30:00Z"
    }
  ],
  "anomalies": [
    {
      "description": "Memory exhaustion in web-app-pod-1",
      "severity": "critical",
      "affected_pods": ["web-app-pod-1"],
      "first_seen": "2026-02-05T10:30:00Z",
      "occurrences": 3
    }
  ],
  "recommendations": [
    "Increase memory limits for affected pods",
    "Check memory usage patterns and optimize application"
  ]
}
```

## Implementation Details

### Error Detection Algorithm

1. **Pattern Matching**: Scan log messages for known error patterns using regex
2. **Error Extraction**: Extract error type, pod name, message, and timestamp
3. **Deduplication**: Group similar errors by type and pod

### LLM Analysis Process

1. **Log Preparation**: Format recent logs (up to 100 entries) for LLM context
2. **Prompt Construction**: Create structured prompt with error summary and logs
3. **LLM Request**: Send to configured LLM with low temperature (0.3) for focused analysis
4. **Response Parsing**: Extract summary, severity, anomalies, and recommendations
5. **Result Combination**: Merge LLM insights with pattern-detected errors

### Prompt Strategy

The service uses a structured prompt format:

```
You are a Kubernetes expert analyzing application logs. Your task is to:
1. Identify anomalies and unusual patterns in the logs
2. Assess the overall severity of issues (critical, warning, info, normal)
3. Provide a concise summary of the system state
4. Generate specific, actionable recommendations

Pre-detected errors:
- OOMKilled: 2 occurrences
- CrashLoopBackOff: 1 occurrence

Recent logs:
[timestamp] [level] Pod: pod-name | Container: container-name | message
...

Please provide your analysis in the following format:

SUMMARY:
[2-3 sentence summary]

SEVERITY:
[critical, warning, info, or normal]

ANOMALIES:
[severity|description|affected_pods]

RECOMMENDATIONS:
[actionable recommendations]
```

### Error Handling

The service implements robust error handling:

- **LLM Failure**: Falls back to pattern-detected errors with basic recommendations
- **No Logs**: Returns informative message suggesting verification steps
- **Invalid Deployment**: Returns 404 with clear error message
- **Missing LLM Config**: Returns 503 with configuration guidance

## Testing

### Unit Tests

Located in `backend/tests/test_ai_analyzer.py`:

- ✅ Error detection for OOMKilled, CrashLoopBackOff, ImagePullBackOff
- ✅ Recommendation generation for each error type
- ✅ Full log analysis with LLM
- ✅ LLM failure handling
- ✅ Log context preparation
- ✅ API endpoint success and error cases

**Test Results:** All 10 tests passing

### Example Usage

See `backend/tests/example_ai_analyzer_usage.py` for a complete example demonstrating:

- Service initialization
- Log analysis with sample data
- Result interpretation
- Error detection and recommendations

## Configuration

### Environment Variables

Add to `.env` file:

```bash
# LLM Provider API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OLLAMA_ENDPOINT=http://localhost:11434
```

### Model Selection

Supported models:
- **OpenAI**: gpt-4, gpt-3.5-turbo
- **Anthropic**: claude-3-sonnet, claude-3-opus
- **Google**: gemini-pro
- **Ollama**: llama2, mistral (local models)

## Performance Considerations

### Log Limits

- Maximum 500 log entries per analysis request
- Most recent logs prioritized
- Configurable via `max_entries` parameter

### Context Window Management

- Logs formatted efficiently for LLM context
- Automatic truncation if needed
- Summarization for very large log sets

### Caching

Future enhancement: Cache analysis results for identical log sets to reduce LLM API costs.

## Security

### API Key Protection

- API keys stored encrypted in database (AES-256)
- Keys loaded from environment variables
- Never exposed in API responses

### Input Validation

- Deployment ownership verified
- Time ranges validated
- Log content sanitized

## Future Enhancements

1. **Historical Analysis**: Track error trends over time
2. **Automated Remediation**: Suggest kubectl commands to fix issues
3. **Alert Integration**: Automatically trigger alerts for critical issues
4. **Cost Optimization**: Cache analysis results to reduce LLM API calls
5. **Multi-Cluster Analysis**: Compare issues across multiple clusters
6. **Custom Error Patterns**: Allow users to define custom error patterns

## Related Documentation

- [Monitor Service Implementation](./MONITOR_SERVICE_IMPLEMENTATION.md)
- [LLM Router Implementation](./LLM_ROUTER_IMPLEMENTATION.md)
- [Requirements Document](../../.kiro/specs/devops-k8s-platform/requirements.md)
- [Design Document](../../.kiro/specs/devops-k8s-platform/design.md)

## Completion Status

✅ **Task 20.1**: Implement log analysis with LLM - COMPLETED  
✅ **Task 20.2**: Create log analysis endpoint - COMPLETED  
✅ **Task 20**: Backend AI Analyzer Service - COMPLETED

All requirements validated:
- ✅ Requirement 10.1: LLM-based log analysis
- ✅ Requirement 10.2: Anomaly detection
- ✅ Requirement 10.3: Common error identification
- ✅ Requirement 10.4: Summary with severity levels
- ✅ Requirement 10.6: Actionable recommendations
