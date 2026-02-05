"""
Cost Estimation Service for calculating cloud provider costs.

This service calculates estimated monthly costs for Kubernetes deployments
based on resource requirements and cloud provider pricing models.
"""

import yaml
import re
from typing import Dict, List, Tuple
from datetime import datetime

from app.schemas import (
    KubernetesManifest,
    ResourceRequirements,
    CostBreakdown,
    CostEstimateResponse
)


class CostEstimationService:
    """
    Service for estimating cloud costs based on Kubernetes manifests.
    
    Supports pricing models for:
    - GKE (Google Kubernetes Engine)
    - EKS (Amazon Elastic Kubernetes Service)
    - AKS (Azure Kubernetes Service)
    """
    
    # Pricing models (USD per month)
    # These are approximate standard pricing as of 2024
    PRICING = {
        "gke": {
            "cpu_per_core": 33.00,  # ~$0.045/hour * 730 hours
            "memory_per_gb": 3.65,  # ~$0.005/GB/hour * 730 hours
            "storage_per_gb": 0.17,  # Standard persistent disk
        },
        "eks": {
            "cpu_per_core": 29.20,  # ~$0.04/hour * 730 hours
            "memory_per_gb": 3.28,  # ~$0.0045/GB/hour * 730 hours
            "storage_per_gb": 0.10,  # EBS gp3 storage
        },
        "aks": {
            "cpu_per_core": 31.39,  # ~$0.043/hour * 730 hours
            "memory_per_gb": 3.50,  # ~$0.0048/GB/hour * 730 hours
            "storage_per_gb": 0.15,  # Standard SSD
        }
    }
    
    def calculate_resources(
        self,
        manifests: List[KubernetesManifest]
    ) -> ResourceRequirements:
        """
        Calculate total resource requirements from Kubernetes manifests.
        
        Sums CPU requests, memory requests, and storage requirements across
        all Deployments, StatefulSets, and PersistentVolumeClaims.
        
        Args:
            manifests: List of Kubernetes manifests
            
        Returns:
            ResourceRequirements with totals
        """
        total_cpu = 0.0
        total_memory_gb = 0.0
        total_storage_gb = 0.0
        total_pods = 0
        
        for manifest in manifests:
            try:
                manifest_dict = yaml.safe_load(manifest.content)
                kind = manifest_dict.get("kind", "")
                
                if kind in ["Deployment", "StatefulSet", "DaemonSet"]:
                    cpu, memory, pods = self._extract_deployment_resources(manifest_dict)
                    total_cpu += cpu
                    total_memory_gb += memory
                    total_pods += pods
                    
                elif kind == "PersistentVolumeClaim":
                    storage = self._extract_storage_resources(manifest_dict)
                    total_storage_gb += storage
                    
            except Exception as e:
                # Skip manifests that can't be parsed
                print(f"Warning: Could not parse manifest {manifest.name}: {e}")
                continue
        
        return ResourceRequirements(
            cpu_cores=round(total_cpu, 2),
            memory_gb=round(total_memory_gb, 2),
            storage_gb=round(total_storage_gb, 2),
            pod_count=total_pods
        )
    
    def _extract_deployment_resources(
        self,
        manifest: Dict
    ) -> Tuple[float, float, int]:
        """
        Extract CPU, memory, and replica count from a Deployment/StatefulSet.
        
        Args:
            manifest: Parsed manifest dictionary
            
        Returns:
            Tuple of (cpu_cores, memory_gb, pod_count)
        """
        cpu_cores = 0.0
        memory_gb = 0.0
        replicas = 1
        
        # Get replica count
        spec = manifest.get("spec", {})
        replicas = spec.get("replicas", 1)
        
        # Get container resources
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        containers = pod_spec.get("containers", [])
        
        for container in containers:
            resources = container.get("resources", {})
            requests = resources.get("requests", {})
            
            # Parse CPU (can be in cores like "0.5" or millicores like "500m")
            cpu_str = requests.get("cpu", "0")
            cpu_cores += self._parse_cpu(cpu_str)
            
            # Parse memory (can be in various units like "512Mi", "1Gi", "1024M")
            memory_str = requests.get("memory", "0")
            memory_gb += self._parse_memory(memory_str)
        
        # Multiply by replicas
        total_cpu = cpu_cores * replicas
        total_memory = memory_gb * replicas
        total_pods = replicas
        
        return total_cpu, total_memory, total_pods
    
    def _extract_storage_resources(self, manifest: Dict) -> float:
        """
        Extract storage size from a PersistentVolumeClaim.
        
        Args:
            manifest: Parsed PVC manifest dictionary
            
        Returns:
            Storage size in GB
        """
        spec = manifest.get("spec", {})
        resources = spec.get("resources", {})
        requests = resources.get("requests", {})
        storage_str = requests.get("storage", "0")
        
        return self._parse_storage(storage_str)
    
    def _parse_cpu(self, cpu_str: str) -> float:
        """
        Parse CPU string to cores.
        
        Examples:
            "0.5" -> 0.5
            "500m" -> 0.5
            "1" -> 1.0
            "2000m" -> 2.0
        
        Args:
            cpu_str: CPU string from Kubernetes manifest
            
        Returns:
            CPU in cores
        """
        if not cpu_str or cpu_str == "0":
            return 0.0
        
        cpu_str = str(cpu_str).strip()
        
        # Handle millicores (e.g., "500m")
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000.0
        
        # Handle cores (e.g., "0.5", "1", "2")
        return float(cpu_str)
    
    def _parse_memory(self, memory_str: str) -> float:
        """
        Parse memory string to GB.
        
        Examples:
            "512Mi" -> 0.5
            "1Gi" -> 1.0
            "1024M" -> 1.0
            "2G" -> 2.0
        
        Args:
            memory_str: Memory string from Kubernetes manifest
            
        Returns:
            Memory in GB
        """
        if not memory_str or memory_str == "0":
            return 0.0
        
        memory_str = str(memory_str).strip()
        
        # Extract number and unit
        match = re.match(r"^(\d+(?:\.\d+)?)\s*([A-Za-z]*)$", memory_str)
        if not match:
            return 0.0
        
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        # Convert to GB
        if unit in ["GI", "G"]:
            return value
        elif unit in ["MI", "M"]:
            return value / 1024.0
        elif unit in ["KI", "K"]:
            return value / (1024.0 * 1024.0)
        elif unit in ["TI", "T"]:
            return value * 1024.0
        else:
            # Assume bytes if no unit
            return value / (1024.0 * 1024.0 * 1024.0)
    
    def _parse_storage(self, storage_str: str) -> float:
        """
        Parse storage string to GB.
        
        Same logic as _parse_memory since storage uses the same units.
        
        Args:
            storage_str: Storage string from Kubernetes manifest
            
        Returns:
            Storage in GB
        """
        return self._parse_memory(storage_str)
    
    def calculate_cost(
        self,
        resources: ResourceRequirements,
        cloud_provider: str
    ) -> CostBreakdown:
        """
        Calculate estimated monthly cost based on resources and provider.
        
        Args:
            resources: Resource requirements
            cloud_provider: Cloud provider (gke, eks, aks)
            
        Returns:
            CostBreakdown with itemized costs
            
        Raises:
            ValueError: If cloud provider is not supported
        """
        provider = cloud_provider.lower()
        
        if provider not in self.PRICING:
            raise ValueError(
                f"Unsupported cloud provider: {cloud_provider}. "
                f"Supported providers: {', '.join(self.PRICING.keys())}"
            )
        
        pricing = self.PRICING[provider]
        
        # Calculate costs
        cpu_cost = resources.cpu_cores * pricing["cpu_per_core"]
        memory_cost = resources.memory_gb * pricing["memory_per_gb"]
        storage_cost = resources.storage_gb * pricing["storage_per_gb"]
        total_cost = cpu_cost + memory_cost + storage_cost
        
        return CostBreakdown(
            cpu_cost=round(cpu_cost, 2),
            memory_cost=round(memory_cost, 2),
            storage_cost=round(storage_cost, 2),
            total_cost=round(total_cost, 2)
        )
    
    def estimate_deployment_cost(
        self,
        deployment_id: str,
        manifests: List[KubernetesManifest],
        cloud_provider: str = "gke"
    ) -> CostEstimateResponse:
        """
        Generate complete cost estimate for a deployment.
        
        Args:
            deployment_id: Deployment identifier
            manifests: List of Kubernetes manifests
            cloud_provider: Cloud provider for pricing (default: gke)
            
        Returns:
            CostEstimateResponse with complete cost breakdown
        """
        # Calculate resource requirements
        resources = self.calculate_resources(manifests)
        
        # Calculate costs
        cost_breakdown = self.calculate_cost(resources, cloud_provider)
        
        return CostEstimateResponse(
            deployment_id=deployment_id,
            cloud_provider=cloud_provider,
            resources=resources,
            cost_breakdown=cost_breakdown,
            estimated_monthly_cost=cost_breakdown.total_cost,
            timestamp=datetime.utcnow()
        )
