"""
Parser Service for validating and extracting Docker Compose structure.
"""
import yaml
from typing import Dict, Any, List, Optional
from yaml.scanner import ScannerError
from yaml.parser import ParserError as YAMLParserError

from app.schemas import (
    ComposeStructure,
    ServiceDefinition,
    VolumeDefinition,
    NetworkDefinition,
    PortMapping,
    ValidationResult,
    ValidationError,
)


class ParserService:
    """Service for parsing and validating Docker Compose files."""

    def validate_yaml(self, content: str) -> ValidationResult:
        """
        Validate YAML syntax and return errors if any.
        
        Args:
            content: YAML content as string
            
        Returns:
            ValidationResult with valid flag and any errors
        """
        try:
            yaml.safe_load(content)
            return ValidationResult(valid=True, errors=[])
        except ScannerError as e:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        line=e.problem_mark.line + 1 if e.problem_mark else None,
                        column=e.problem_mark.column + 1 if e.problem_mark else None,
                        message=e.problem or "YAML scanning error",
                        error_type="ScannerError",
                    )
                ],
            )
        except YAMLParserError as e:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        line=e.problem_mark.line + 1 if e.problem_mark else None,
                        column=e.problem_mark.column + 1 if e.problem_mark else None,
                        message=e.problem or "YAML parsing error",
                        error_type="ParserError",
                    )
                ],
            )
        except yaml.YAMLError as e:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        line=None,
                        column=None,
                        message=str(e),
                        error_type="YAMLError",
                    )
                ],
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        line=None,
                        column=None,
                        message=f"Unexpected error: {str(e)}",
                        error_type="UnexpectedError",
                    )
                ],
            )

    def parse_compose(self, content: str) -> ComposeStructure:
        """
        Extract services, volumes, networks, and dependencies from Docker Compose.
        
        Args:
            content: Valid Docker Compose YAML content
            
        Returns:
            ComposeStructure with all extracted components
            
        Raises:
            ValueError: If YAML is invalid or not a valid Docker Compose file
        """
        # First validate the YAML
        validation = self.validate_yaml(content)
        if not validation.valid:
            error_messages = [e.message for e in validation.errors]
            raise ValueError(f"Invalid YAML: {'; '.join(error_messages)}")

        # Parse the YAML
        try:
            compose_dict = yaml.safe_load(content)
        except Exception as e:
            raise ValueError(f"Failed to parse YAML: {str(e)}")

        if not isinstance(compose_dict, dict):
            raise ValueError("Docker Compose file must be a YAML dictionary")

        # Extract version
        version = compose_dict.get("version")

        # Extract services
        services = self.extract_services(compose_dict)

        # Extract volumes
        volumes = self.extract_volumes(compose_dict)

        # Extract networks
        networks = self.extract_networks(compose_dict)

        return ComposeStructure(
            services=services,
            volumes=volumes,
            networks=networks,
            version=version,
        )

    def extract_services(self, compose_dict: Dict[str, Any]) -> List[ServiceDefinition]:
        """
        Parse service definitions from compose dictionary.
        
        Args:
            compose_dict: Parsed Docker Compose dictionary
            
        Returns:
            List of ServiceDefinition objects
        """
        services = []
        services_dict = compose_dict.get("services", {})

        if not isinstance(services_dict, dict):
            return services

        for service_name, service_config in services_dict.items():
            if not isinstance(service_config, dict):
                continue

            # Extract ports
            ports = self._extract_ports(service_config.get("ports", []))

            # Extract environment variables
            environment = self._extract_environment(service_config.get("environment", {}))

            # Extract volumes
            volumes = self._extract_service_volumes(service_config.get("volumes", []))

            # Extract depends_on
            depends_on = self._extract_depends_on(service_config.get("depends_on", []))

            # Extract networks
            networks = self._extract_service_networks(service_config.get("networks", []))

            # Extract command
            command = service_config.get("command")
            if isinstance(command, list):
                command = " ".join(str(c) for c in command)
            elif command is not None:
                command = str(command)

            service = ServiceDefinition(
                name=service_name,
                image=service_config.get("image"),
                build=service_config.get("build"),
                ports=ports,
                environment=environment,
                volumes=volumes,
                depends_on=depends_on,
                command=command,
                networks=networks,
            )
            services.append(service)

        return services

    def extract_volumes(self, compose_dict: Dict[str, Any]) -> List[VolumeDefinition]:
        """
        Extract volume definitions from compose dictionary.
        
        Args:
            compose_dict: Parsed Docker Compose dictionary
            
        Returns:
            List of VolumeDefinition objects
        """
        volumes = []
        volumes_dict = compose_dict.get("volumes", {})

        if not isinstance(volumes_dict, dict):
            return volumes

        for volume_name, volume_config in volumes_dict.items():
            # Handle null/empty volume definitions
            if volume_config is None:
                volume_config = {}

            if not isinstance(volume_config, dict):
                continue

            volume = VolumeDefinition(
                name=volume_name,
                driver=volume_config.get("driver"),
                driver_opts=volume_config.get("driver_opts", {}),
                external=volume_config.get("external", False),
            )
            volumes.append(volume)

        return volumes

    def extract_networks(self, compose_dict: Dict[str, Any]) -> List[NetworkDefinition]:
        """
        Extract network definitions from compose dictionary.
        
        Args:
            compose_dict: Parsed Docker Compose dictionary
            
        Returns:
            List of NetworkDefinition objects
        """
        networks = []
        networks_dict = compose_dict.get("networks", {})

        if not isinstance(networks_dict, dict):
            return networks

        for network_name, network_config in networks_dict.items():
            # Handle null/empty network definitions
            if network_config is None:
                network_config = {}

            if not isinstance(network_config, dict):
                continue

            network = NetworkDefinition(
                name=network_name,
                driver=network_config.get("driver"),
                external=network_config.get("external", False),
                ipam=network_config.get("ipam"),
            )
            networks.append(network)

        return networks

    def _extract_ports(self, ports_config: Any) -> List[PortMapping]:
        """Extract port mappings from service configuration."""
        ports = []

        if not isinstance(ports_config, list):
            return ports

        for port in ports_config:
            if isinstance(port, str):
                # Handle "8080:80" or "80" format
                if ":" in port:
                    parts = port.split(":")
                    if len(parts) == 2:
                        ports.append(
                            PortMapping(host=parts[0], container=parts[1])
                        )
                    elif len(parts) == 3:
                        # Handle "127.0.0.1:8080:80" format
                        ports.append(
                            PortMapping(host=parts[1], container=parts[2])
                        )
                else:
                    ports.append(PortMapping(container=port))
            elif isinstance(port, dict):
                # Handle long format
                target = port.get("target", port.get("published"))
                published = port.get("published", port.get("target"))
                protocol = port.get("protocol", "tcp")
                
                if target:
                    ports.append(
                        PortMapping(
                            host=str(published) if published else None,
                            container=str(target),
                            protocol=protocol,
                        )
                    )

        return ports

    def _extract_environment(self, env_config: Any) -> Dict[str, str]:
        """Extract environment variables from service configuration."""
        environment = {}

        if isinstance(env_config, dict):
            # Handle dictionary format
            for key, value in env_config.items():
                environment[key] = str(value) if value is not None else ""
        elif isinstance(env_config, list):
            # Handle list format ["KEY=value", "KEY2=value2"]
            for item in env_config:
                if isinstance(item, str) and "=" in item:
                    key, value = item.split("=", 1)
                    environment[key] = value

        return environment

    def _extract_service_volumes(self, volumes_config: Any) -> List[str]:
        """Extract volume mounts from service configuration."""
        volumes = []

        if not isinstance(volumes_config, list):
            return volumes

        for volume in volumes_config:
            if isinstance(volume, str):
                volumes.append(volume)
            elif isinstance(volume, dict):
                # Handle long format
                source = volume.get("source", "")
                target = volume.get("target", "")
                if source and target:
                    volumes.append(f"{source}:{target}")
                elif target:
                    volumes.append(target)

        return volumes

    def _extract_depends_on(self, depends_config: Any) -> List[str]:
        """Extract service dependencies from configuration."""
        depends_on = []

        if isinstance(depends_config, list):
            # Handle list format
            depends_on = [str(dep) for dep in depends_config]
        elif isinstance(depends_config, dict):
            # Handle dictionary format (with conditions)
            depends_on = list(depends_config.keys())

        return depends_on

    def _extract_service_networks(self, networks_config: Any) -> List[str]:
        """Extract network connections from service configuration."""
        networks = []

        if isinstance(networks_config, list):
            # Handle list format
            networks = [str(net) for net in networks_config]
        elif isinstance(networks_config, dict):
            # Handle dictionary format (with aliases)
            networks = list(networks_config.keys())

        return networks
