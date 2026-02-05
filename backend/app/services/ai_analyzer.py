"""
AI Analyzer Service for intelligent log analysis.

This service uses LLMs to analyze Kubernetes logs, detect anomalies,
identify common errors, and provide actionable recommendations.
"""
import re
from typing import List, Optional
from datetime import datetime
import logging

from .llm_router import LLMRouter, ModelParameters
from ..schemas import (
    LogEntry,
    AnalysisResult,
    Anomaly,
    KubernetesError
)

logger = logging.getLogger(__name__)


class AIAnalyzerService:
    """
    Service for AI-powered log analysis.
    
    Provides intelligent analysis of Kubernetes logs including:
    - Anomaly detection
    - Common error identification (OOMKilled, CrashLoopBackOff, ImagePullBackOff)
    - Severity classification
    - Actionable recommendations
    """
    
    def __init__(self, llm_router: LLMRouter):
        """
        Initialize AI Analyzer Service.
        
        Args:
            llm_router: LLM Router for AI model access
        """
        self.llm_router = llm_router
        
        # Common Kubernetes error patterns
        self.error_patterns = {
            "OOMKilled": r"OOMKilled|Out of memory|oom-kill",
            "CrashLoopBackOff": r"CrashLoopBackOff|Back-off restarting failed container",
            "ImagePullBackOff": r"ImagePullBackOff|Failed to pull image|ErrImagePull",
            "PodEvicted": r"Evicted|The node was low on resource",
            "ContainerCreating": r"ContainerCreating.*timeout|Failed to create container",
            "NetworkError": r"network.*unreachable|connection refused|timeout.*dial",
            "VolumeMount": r"Unable to mount volumes|MountVolume.SetUp failed",
            "ConfigError": r"InvalidImageName|CreateContainerConfigError"
        }
    
    def analyze_logs(
        self,
        logs: List[LogEntry],
        model: str = "gpt-4",
        parameters: Optional[ModelParameters] = None
    ) -> AnalysisResult:
        """
        Analyze logs using LLM to detect issues and provide recommendations.
        
        Args:
            logs: List of log entries to analyze
            model: LLM model to use for analysis
            parameters: Optional model parameters
            
        Returns:
            AnalysisResult with summary, anomalies, errors, and recommendations
        """
        logger.info(f"Starting log analysis with {len(logs)} log entries using model {model}")
        
        # First, detect common Kubernetes errors using pattern matching
        common_errors = self.detect_common_errors(logs)
        logger.info(f"Detected {len(common_errors)} common Kubernetes errors")
        
        # Prepare logs for LLM analysis
        log_context = self._prepare_log_context(logs, max_entries=100)
        
        # Create analysis prompt
        prompt = self._create_analysis_prompt(log_context, common_errors)
        
        # Use default parameters if not provided
        if parameters is None:
            parameters = ModelParameters(
                temperature=0.3,  # Lower temperature for more focused analysis
                max_tokens=2000
            )
        
        try:
            # Get analysis from LLM
            llm_response = self.llm_router.generate(
                prompt=prompt,
                model=model,
                parameters=parameters
            )
            
            # Parse LLM response into structured result
            analysis_result = self._parse_llm_response(llm_response, common_errors)
            
            logger.info(f"Analysis complete. Severity: {analysis_result.severity}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error during LLM analysis: {str(e)}")
            # Return basic analysis with detected errors
            return AnalysisResult(
                summary=f"Analysis failed due to LLM error. Detected {len(common_errors)} common errors.",
                anomalies=[],
                common_errors=common_errors,
                recommendations=self.generate_recommendations(common_errors),
                severity="warning" if common_errors else "info"
            )
    
    def detect_common_errors(self, logs: List[LogEntry]) -> List[KubernetesError]:
        """
        Detect common Kubernetes errors using pattern matching.
        
        Args:
            logs: List of log entries to scan
            
        Returns:
            List of detected Kubernetes errors
        """
        detected_errors = []
        
        for log in logs:
            for error_type, pattern in self.error_patterns.items():
                if re.search(pattern, log.message, re.IGNORECASE):
                    error = KubernetesError(
                        error_type=error_type,
                        pod_name=log.pod_name,
                        message=log.message[:200],  # Truncate long messages
                        timestamp=log.timestamp
                    )
                    detected_errors.append(error)
                    logger.debug(f"Detected {error_type} in pod {log.pod_name}")
        
        return detected_errors
    
    def generate_recommendations(self, errors: List[KubernetesError]) -> List[str]:
        """
        Generate actionable recommendations based on detected errors.
        
        Args:
            errors: List of detected Kubernetes errors
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        error_types = {error.error_type for error in errors}
        
        if "OOMKilled" in error_types:
            recommendations.append(
                "Increase memory limits for affected pods. "
                "Check memory usage patterns and consider optimizing application memory consumption."
            )
        
        if "CrashLoopBackOff" in error_types:
            recommendations.append(
                "Investigate application startup failures. "
                "Check application logs for errors, verify configuration, and ensure dependencies are available."
            )
        
        if "ImagePullBackOff" in error_types:
            recommendations.append(
                "Verify image names and tags are correct. "
                "Check image registry credentials and network connectivity to the registry."
            )
        
        if "PodEvicted" in error_types:
            recommendations.append(
                "Pods were evicted due to resource pressure. "
                "Increase node resources or reduce resource requests for pods."
            )
        
        if "NetworkError" in error_types:
            recommendations.append(
                "Network connectivity issues detected. "
                "Check service endpoints, DNS resolution, and network policies."
            )
        
        if "VolumeMount" in error_types:
            recommendations.append(
                "Volume mounting failed. "
                "Verify PersistentVolumeClaims exist and are bound, check storage class configuration."
            )
        
        if "ConfigError" in error_types:
            recommendations.append(
                "Configuration errors detected. "
                "Review pod specifications, image names, and container configurations."
            )
        
        if not recommendations:
            recommendations.append(
                "No critical issues detected. Continue monitoring for anomalies."
            )
        
        return recommendations
    
    def _prepare_log_context(self, logs: List[LogEntry], max_entries: int = 100) -> str:
        """
        Prepare log entries for LLM context.
        
        Args:
            logs: List of log entries
            max_entries: Maximum number of entries to include
            
        Returns:
            Formatted log context string
        """
        # Sort logs by timestamp
        sorted_logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)
        
        # Take most recent entries
        recent_logs = sorted_logs[:max_entries]
        
        # Format logs
        log_lines = []
        for log in recent_logs:
            timestamp_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            log_lines.append(
                f"[{timestamp_str}] [{log.level.upper()}] "
                f"Pod: {log.pod_name} | Container: {log.container_name} | "
                f"{log.message}"
            )
        
        return "\n".join(log_lines)
    
    def _create_analysis_prompt(
        self,
        log_context: str,
        common_errors: List[KubernetesError]
    ) -> str:
        """
        Create analysis prompt for LLM.
        
        Args:
            log_context: Formatted log entries
            common_errors: Pre-detected common errors
            
        Returns:
            Analysis prompt string
        """
        error_summary = ""
        if common_errors:
            error_types = {}
            for error in common_errors:
                error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
            
            error_summary = "Pre-detected errors:\n"
            for error_type, count in error_types.items():
                error_summary += f"- {error_type}: {count} occurrences\n"
        
        prompt = f"""You are a Kubernetes expert analyzing application logs. Your task is to:
1. Identify anomalies and unusual patterns in the logs
2. Assess the overall severity of issues (critical, warning, info, normal)
3. Provide a concise summary of the system state
4. Generate specific, actionable recommendations

{error_summary}

Recent logs:
{log_context}

Please provide your analysis in the following format:

SUMMARY:
[A concise 2-3 sentence summary of the overall system state and key issues]

SEVERITY:
[One word: critical, warning, info, or normal]

ANOMALIES:
[List any unusual patterns or anomalies, one per line, in format: "severity|description|affected_pods"]

RECOMMENDATIONS:
[List specific, actionable recommendations, one per line]

Focus on practical insights that help operators understand and resolve issues quickly."""
        
        return prompt
    
    def _parse_llm_response(
        self,
        llm_response: str,
        common_errors: List[KubernetesError]
    ) -> AnalysisResult:
        """
        Parse LLM response into structured AnalysisResult.
        
        Args:
            llm_response: Raw LLM response text
            common_errors: Pre-detected common errors
            
        Returns:
            Structured AnalysisResult
        """
        # Extract sections from response
        summary = self._extract_section(llm_response, "SUMMARY")
        severity = self._extract_section(llm_response, "SEVERITY").strip().lower()
        anomalies_text = self._extract_section(llm_response, "ANOMALIES")
        recommendations_text = self._extract_section(llm_response, "RECOMMENDATIONS")
        
        # Validate severity
        if severity not in ["critical", "warning", "info", "normal"]:
            severity = "warning"
        
        # Parse anomalies
        anomalies = self._parse_anomalies(anomalies_text)
        
        # Parse recommendations
        recommendations = [
            rec.strip("- ").strip()
            for rec in recommendations_text.split("\n")
            if rec.strip() and rec.strip() != "-"
        ]
        
        # Add generated recommendations for common errors
        error_recommendations = self.generate_recommendations(common_errors)
        recommendations.extend(error_recommendations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return AnalysisResult(
            summary=summary.strip() or "Log analysis completed.",
            anomalies=anomalies,
            common_errors=common_errors,
            recommendations=unique_recommendations,
            severity=severity
        )
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """
        Extract a section from LLM response.
        
        Args:
            text: Full LLM response
            section_name: Section name to extract
            
        Returns:
            Section content
        """
        pattern = rf"{section_name}:\s*\n(.*?)(?=\n[A-Z]+:|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        return ""
    
    def _parse_anomalies(self, anomalies_text: str) -> List[Anomaly]:
        """
        Parse anomalies from text.
        
        Args:
            anomalies_text: Text containing anomaly descriptions
            
        Returns:
            List of Anomaly objects
        """
        anomalies = []
        
        for line in anomalies_text.split("\n"):
            line = line.strip("- ").strip()
            if not line:
                continue
            
            # Try to parse format: "severity|description|affected_pods"
            parts = line.split("|")
            
            if len(parts) >= 2:
                severity = parts[0].strip().lower()
                description = parts[1].strip()
                affected_pods = parts[2].strip().split(",") if len(parts) > 2 else []
                affected_pods = [pod.strip() for pod in affected_pods if pod.strip()]
            else:
                # Fallback: treat entire line as description
                severity = "warning"
                description = line
                affected_pods = []
            
            # Validate severity
            if severity not in ["critical", "warning", "info"]:
                severity = "warning"
            
            anomaly = Anomaly(
                description=description,
                severity=severity,
                affected_pods=affected_pods,
                first_seen=datetime.now(),
                occurrences=1
            )
            anomalies.append(anomaly)
        
        return anomalies


# Singleton instance
_ai_analyzer_service: Optional[AIAnalyzerService] = None


def get_ai_analyzer_service(llm_router: LLMRouter) -> AIAnalyzerService:
    """
    Get or create AI Analyzer Service instance.
    
    Args:
        llm_router: LLM Router instance
        
    Returns:
        AIAnalyzerService instance
    """
    global _ai_analyzer_service
    
    if _ai_analyzer_service is None:
        _ai_analyzer_service = AIAnalyzerService(llm_router)
    
    return _ai_analyzer_service
