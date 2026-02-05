"""
Converter Service for transforming Docker Compose to Kubernetes manifests using LLMs
"""

import time
import logging
from typing import List, Dict, Any, Optional
from app.schemas import (
    ComposeStructure,
    ServiceDefinition,
    KubernetesManifest,
)
from app.services.llm_router import LLMRouter, ModelParameters
from app.services.cache import CacheService

logger = logging.getLogger(__name__)


class ConverterService:
    """Service for converting Docker Compose to Kubernetes manifests using AI"""
    
    def __init__(self, llm_router: LLMRouter, cache: CacheService):
        """
        Initialize Converter Service
        
        Args:
            llm_router: LLM Router for AI generation
            cache: Cache service for storing conversion results
        """
        self.llm_router = llm_router
        self.cache = cache
    
    def convert_to_k8s(
        self,
        compose: ComposeStructure,
        compose_content: str,
        model: str,
        parameters: Optional[ModelParameters] = None
    ) -> tuple[List[KubernetesManifest], bool, float]:
        """
        Convert Docker Compose to Kubernetes manifests
        
        Args:
            compose: Parsed Docker Compose structure
            compose_content: Original Docker Compose YAML content
            model: LLM model to use for conversion
            parameters: Optional model parameters
            
        Returns:
            Tuple of (manifests, cached, conversion_time)
        """
        start_time = time.time()
        
        # Check cache first
        compose_hash = self.cache.hash_compose(compose_content)
        cached_result = self.cache.get_cached_conversion(compose_hash)
        
        if cached_result:
            # Return cached manifests
            manifests = [
                KubernetesManifest(**manifest) 
                for manifest in cached_result.get('manifests', [])
            ]
            conversion_time = time.time() - start_time
            logger.info(f"Returning cached conversion result (hash: {compose_hash})")
            return manifests, True, conversion_time
        
        # Generate manifests using LLM
        logger.info(f"Generating Kubernetes manifests using {model}")
        
        if parameters is None:
            parameters = ModelParameters()
        
        # Build the conversion prompt
        prompt = self._build_conversion_prompt(compose, compose_content)
        
        # Set system prompt for Kubernetes expert role
        if not parameters.system_prompt:
            parameters.system_prompt = self._get_system_prompt()
        
        # Generate manifests using LLM
        try:
            response = self.llm_router.generate(
                prompt=prompt,
                model=model,
                parameters=parameters
            )
            
            # Parse the LLM response into manifests
            manifests = self._parse_llm_response(response, compose)
            
            # Apply best practices to all manifests
            manifests = self._apply_best_practices(manifests, compose)
            
            # Cache the result
            manifest_dicts = [manifest.model_dump() for manifest in manifests]
            self.cache.cache_conversion(compose_hash, manifest_dicts)
            
            conversion_time = time.time() - start_time
            logger.info(
                f"Successfully generated {len(manifests)} Kubernetes manifests "
                f"in {conversion_time:.2f}s"
            )
            
            return manifests, False, conversion_time
            
        except Exception as e:
            logger.error(f"Failed to convert Docker Compose to Kubernetes: {str(e)}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for Kubernetes conversion"""
        return """You are an expert Kubernetes architect and DevOps engineer. Your task is to convert Docker Compose configurations into production-ready Kubernetes manifests.

Follow these guidelines:
1. Generate separate YAML manifests for each Kubernetes resource type
2. Apply Kubernetes best practices including:
   - Health checks (liveness and readiness probes)
   - Resource limits and requests (CPU and memory)
   - Rolling update strategies
   - Security contexts (non-root users, read-only filesystems where possible)
3. Use appropriate Kubernetes resource types:
   - Deployment for stateless services
   - StatefulSet for stateful services (databases)
   - Service for network exposure
   - ConfigMap for non-sensitive configuration
   - Secret for sensitive data
   - PersistentVolumeClaim for persistent storage
   - Ingress for external HTTP/HTTPS access
4. Maintain service dependencies and relationships
5. Use meaningful labels and selectors
6. Set appropriate namespace (default if not specified)

Format your response as separate YAML documents separated by '---'.
Each document should be a complete, valid Kubernetes manifest."""
    
    def _build_conversion_prompt(
        self,
        compose: ComposeStructure,
        compose_content: str
    ) -> str:
        """
        Build the conversion prompt for the LLM
        
        Args:
            compose: Parsed Docker Compose structure
            compose_content: Original Docker Compose YAML content
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Convert the following Docker Compose configuration to Kubernetes manifests:

```yaml
{compose_content}
```

Requirements:
- Generate Deployment manifests for each service ({len(compose.services)} services)
- Generate Service manifests for services with exposed ports
- Generate ConfigMap manifests for environment variables
- Generate Secret manifests for sensitive data (passwords, API keys, tokens)
- Generate PersistentVolumeClaim manifests for volumes ({len(compose.volumes)} volumes)
- Generate Ingress manifests for services that need external access
- Apply Kubernetes best practices (health checks, resource limits, security contexts)
- Maintain service dependencies using init containers or readiness probes

Service details:
"""
        
        for service in compose.services:
            prompt += f"\n- {service.name}:"
            if service.image:
                prompt += f"\n  Image: {service.image}"
            if service.ports:
                prompt += f"\n  Ports: {', '.join([f'{p.host or p.container}:{p.container}' for p in service.ports])}"
            if service.environment:
                prompt += f"\n  Environment variables: {len(service.environment)}"
            if service.volumes:
                prompt += f"\n  Volumes: {len(service.volumes)}"
            if service.depends_on:
                prompt += f"\n  Depends on: {', '.join(service.depends_on)}"
        
        if compose.networks:
            prompt += f"\n\nNetworks: {', '.join([n.name for n in compose.networks])}"
        
        prompt += "\n\nGenerate complete, production-ready Kubernetes manifests with all best practices applied."
        
        return prompt
    
    def _parse_llm_response(
        self,
        response: str,
        compose: ComposeStructure
    ) -> List[KubernetesManifest]:
        """
        Parse LLM response into Kubernetes manifests
        
        Args:
            response: LLM generated response
            compose: Original compose structure for reference
            
        Returns:
            List of KubernetesManifest objects
        """
        manifests = []
        
        # Split response by YAML document separator
        yaml_docs = response.split('---')
        
        for doc in yaml_docs:
            doc = doc.strip()
            if not doc or doc.startswith('#'):
                continue
            
            # Extract kind and name from the YAML
            try:
                import yaml
                parsed = yaml.safe_load(doc)
                
                if not parsed or not isinstance(parsed, dict):
                    continue
                
                kind = parsed.get('kind', 'Unknown')
                metadata = parsed.get('metadata', {})
                name = metadata.get('name', 'unnamed')
                namespace = metadata.get('namespace', 'default')
                
                manifest = KubernetesManifest(
                    kind=kind,
                    name=name,
                    content=doc,
                    namespace=namespace
                )
                manifests.append(manifest)
                
            except Exception as e:
                logger.warning(f"Failed to parse YAML document: {str(e)}")
                continue
        
        logger.info(f"Parsed {len(manifests)} manifests from LLM response")
        return manifests
    
    def _apply_best_practices(
        self,
        manifests: List[KubernetesManifest],
        compose: ComposeStructure
    ) -> List[KubernetesManifest]:
        """
        Apply Kubernetes best practices to manifests
        
        Args:
            manifests: List of generated manifests
            compose: Original compose structure
            
        Returns:
            List of manifests with best practices applied
        """
        # The LLM should already apply best practices based on the system prompt
        # This method can be used for additional validation or enforcement
        
        enhanced_manifests = []
        
        for manifest in manifests:
            try:
                import yaml
                parsed = yaml.safe_load(manifest.content)
                
                if manifest.kind == 'Deployment':
                    parsed = self._enhance_deployment(parsed, compose)
                elif manifest.kind == 'StatefulSet':
                    parsed = self._enhance_statefulset(parsed, compose)
                
                # Convert back to YAML
                enhanced_content = yaml.dump(parsed, default_flow_style=False, sort_keys=False)
                
                enhanced_manifest = KubernetesManifest(
                    kind=manifest.kind,
                    name=manifest.name,
                    content=enhanced_content,
                    namespace=manifest.namespace
                )
                enhanced_manifests.append(enhanced_manifest)
                
            except Exception as e:
                logger.warning(f"Failed to enhance manifest {manifest.name}: {str(e)}")
                # Keep original manifest if enhancement fails
                enhanced_manifests.append(manifest)
        
        return enhanced_manifests
    
    def _enhance_deployment(
        self,
        deployment: Dict[str, Any],
        compose: ComposeStructure
    ) -> Dict[str, Any]:
        """
        Enhance Deployment manifest with best practices
        
        Args:
            deployment: Parsed Deployment manifest
            compose: Original compose structure
            
        Returns:
            Enhanced deployment manifest
        """
        # Ensure spec exists
        if 'spec' not in deployment:
            return deployment
        
        spec = deployment['spec']
        
        # Ensure template exists
        if 'template' not in spec:
            return deployment
        
        template = spec['template']
        
        # Ensure containers exist
        if 'spec' not in template or 'containers' not in template['spec']:
            return deployment
        
        containers = template['spec']['containers']
        
        # Enhance each container
        for container in containers:
            # Add resource limits if not present
            if 'resources' not in container:
                container['resources'] = {
                    'requests': {
                        'cpu': '100m',
                        'memory': '128Mi'
                    },
                    'limits': {
                        'cpu': '500m',
                        'memory': '512Mi'
                    }
                }
            
            # Add liveness probe if not present
            if 'livenessProbe' not in container and container.get('ports'):
                port = container['ports'][0].get('containerPort')
                if port:
                    container['livenessProbe'] = {
                        'httpGet': {
                            'path': '/health',
                            'port': port
                        },
                        'initialDelaySeconds': 30,
                        'periodSeconds': 10
                    }
            
            # Add readiness probe if not present
            if 'readinessProbe' not in container and container.get('ports'):
                port = container['ports'][0].get('containerPort')
                if port:
                    container['readinessProbe'] = {
                        'httpGet': {
                            'path': '/ready',
                            'port': port
                        },
                        'initialDelaySeconds': 5,
                        'periodSeconds': 5
                    }
            
            # Add security context if not present
            if 'securityContext' not in container:
                container['securityContext'] = {
                    'runAsNonRoot': True,
                    'runAsUser': 1000,
                    'allowPrivilegeEscalation': False,
                    'readOnlyRootFilesystem': False
                }
        
        # Add rolling update strategy if not present
        if 'strategy' not in spec:
            spec['strategy'] = {
                'type': 'RollingUpdate',
                'rollingUpdate': {
                    'maxSurge': 1,
                    'maxUnavailable': 0
                }
            }
        
        return deployment
    
    def _enhance_statefulset(
        self,
        statefulset: Dict[str, Any],
        compose: ComposeStructure
    ) -> Dict[str, Any]:
        """
        Enhance StatefulSet manifest with best practices
        
        Args:
            statefulset: Parsed StatefulSet manifest
            compose: Original compose structure
            
        Returns:
            Enhanced statefulset manifest
        """
        # Similar enhancements as Deployment
        return self._enhance_deployment(statefulset, compose)
    
    def generate_deployment(self, service: ServiceDefinition) -> str:
        """
        Generate Deployment manifest for a service
        
        Args:
            service: Service definition from Docker Compose
            
        Returns:
            YAML string for Deployment manifest
        """
        # This is a fallback method if LLM generation fails
        # In normal operation, the LLM generates all manifests
        import yaml
        
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': service.name,
                'labels': {
                    'app': service.name
                }
            },
            'spec': {
                'replicas': 1,
                'selector': {
                    'matchLabels': {
                        'app': service.name
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': service.name
                        }
                    },
                    'spec': {
                        'containers': [
                            {
                                'name': service.name,
                                'image': service.image or 'nginx:latest',
                                'ports': [
                                    {'containerPort': int(p.container)}
                                    for p in service.ports
                                ] if service.ports else [],
                                'env': [
                                    {'name': k, 'value': v}
                                    for k, v in service.environment.items()
                                ] if service.environment else []
                            }
                        ]
                    }
                }
            }
        }
        
        return yaml.dump(deployment, default_flow_style=False, sort_keys=False)
    
    def generate_service(self, service: ServiceDefinition) -> str:
        """
        Generate Service manifest for network exposure
        
        Args:
            service: Service definition from Docker Compose
            
        Returns:
            YAML string for Service manifest
        """
        # This is a fallback method if LLM generation fails
        import yaml
        
        if not service.ports:
            return ""
        
        k8s_service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': service.name,
                'labels': {
                    'app': service.name
                }
            },
            'spec': {
                'selector': {
                    'app': service.name
                },
                'ports': [
                    {
                        'port': int(p.host or p.container),
                        'targetPort': int(p.container),
                        'protocol': p.protocol.upper()
                    }
                    for p in service.ports
                ],
                'type': 'ClusterIP'
            }
        }
        
        return yaml.dump(k8s_service, default_flow_style=False, sort_keys=False)
