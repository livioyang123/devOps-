"""
Unit tests for Parser Service.
Tests YAML validation and Docker Compose parsing functionality.
"""
import pytest
from app.services.parser import ParserService
from app.schemas import (
    ComposeStructure,
    ServiceDefinition,
    VolumeDefinition,
    NetworkDefinition,
    ValidationResult,
)


@pytest.fixture
def parser_service():
    """Create a ParserService instance for testing."""
    return ParserService()


class TestYAMLValidation:
    """Test YAML validation functionality."""

    def test_validate_valid_yaml(self, parser_service):
        """Test validation of valid YAML."""
        valid_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
"""
        result = parser_service.validate_yaml(valid_yaml)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_yaml_syntax(self, parser_service):
        """Test validation of invalid YAML syntax."""
        invalid_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
  - invalid indentation
"""
        result = parser_service.validate_yaml(invalid_yaml)
        assert result.valid is False
        assert len(result.errors) > 0
        assert result.errors[0].line is not None
        assert result.errors[0].message is not None

    def test_validate_empty_yaml(self, parser_service):
        """Test validation of empty YAML."""
        empty_yaml = ""
        result = parser_service.validate_yaml(empty_yaml)
        # Empty YAML is technically valid (parses to None)
        assert result.valid is True

    def test_validate_yaml_with_tabs(self, parser_service):
        """Test validation of YAML with tab characters (invalid in YAML)."""
        yaml_with_tabs = "version: '3.8'\n\tservices:\n\t\tweb:\n\t\t\timage: nginx"
        result = parser_service.validate_yaml(yaml_with_tabs)
        assert result.valid is False
        assert len(result.errors) > 0


class TestComposeStructureExtraction:
    """Test Docker Compose structure extraction."""

    def test_parse_simple_compose(self, parser_service):
        """Test parsing a simple Docker Compose file."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert isinstance(structure, ComposeStructure)
        assert structure.version == '3.8'
        assert len(structure.services) == 1
        assert structure.services[0].name == 'web'
        assert structure.services[0].image == 'nginx:latest'
        assert len(structure.services[0].ports) == 1
        assert structure.services[0].ports[0].host == '8080'
        assert structure.services[0].ports[0].container == '80'

    def test_parse_compose_with_multiple_services(self, parser_service):
        """Test parsing Docker Compose with multiple services."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
  db:
    image: postgres:13
  redis:
    image: redis:alpine
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 3
        service_names = [s.name for s in structure.services]
        assert 'web' in service_names
        assert 'db' in service_names
        assert 'redis' in service_names

    def test_parse_compose_with_environment_dict(self, parser_service):
        """Test parsing environment variables in dictionary format."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    environment:
      NODE_ENV: production
      PORT: 3000
      DEBUG: "true"
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 1
        env = structure.services[0].environment
        assert env['NODE_ENV'] == 'production'
        assert env['PORT'] == '3000'
        assert env['DEBUG'] == 'true'

    def test_parse_compose_with_environment_list(self, parser_service):
        """Test parsing environment variables in list format."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    environment:
      - NODE_ENV=production
      - PORT=3000
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 1
        env = structure.services[0].environment
        assert env['NODE_ENV'] == 'production'
        assert env['PORT'] == '3000'

    def test_parse_compose_with_volumes(self, parser_service):
        """Test parsing Docker Compose with volumes."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    volumes:
      - ./data:/var/www/html
      - logs:/var/log/nginx
volumes:
  logs:
    driver: local
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 1
        assert len(structure.services[0].volumes) == 2
        assert './data:/var/www/html' in structure.services[0].volumes
        
        assert len(structure.volumes) == 1
        assert structure.volumes[0].name == 'logs'
        assert structure.volumes[0].driver == 'local'

    def test_parse_compose_with_networks(self, parser_service):
        """Test parsing Docker Compose with networks."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    networks:
      - frontend
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 1
        assert 'frontend' in structure.services[0].networks
        
        assert len(structure.networks) == 2
        network_names = [n.name for n in structure.networks]
        assert 'frontend' in network_names
        assert 'backend' in network_names

    def test_parse_compose_with_depends_on_list(self, parser_service):
        """Test parsing depends_on in list format."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    depends_on:
      - db
      - redis
  db:
    image: postgres:13
  redis:
    image: redis:alpine
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        web_service = next(s for s in structure.services if s.name == 'web')
        assert len(web_service.depends_on) == 2
        assert 'db' in web_service.depends_on
        assert 'redis' in web_service.depends_on

    def test_parse_compose_with_depends_on_dict(self, parser_service):
        """Test parsing depends_on in dictionary format (with conditions)."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
  db:
    image: postgres:13
  redis:
    image: redis:alpine
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        web_service = next(s for s in structure.services if s.name == 'web')
        assert len(web_service.depends_on) == 2
        assert 'db' in web_service.depends_on
        assert 'redis' in web_service.depends_on

    def test_parse_compose_with_build(self, parser_service):
        """Test parsing service with build configuration."""
        compose_yaml = """
version: '3.8'
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:80"
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 1
        assert structure.services[0].build is not None
        assert structure.services[0].build['context'] == '.'
        assert structure.services[0].build['dockerfile'] == 'Dockerfile'

    def test_parse_compose_with_command(self, parser_service):
        """Test parsing service with command."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    command: nginx -g 'daemon off;'
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 1
        assert structure.services[0].command == "nginx -g 'daemon off;'"

    def test_parse_compose_with_port_long_format(self, parser_service):
        """Test parsing ports in long format."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - target: 80
        published: 8080
        protocol: tcp
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 1
        assert len(structure.services[0].ports) == 1
        port = structure.services[0].ports[0]
        assert port.container == '80'
        assert port.host == '8080'
        assert port.protocol == 'tcp'

    def test_parse_invalid_compose_structure(self, parser_service):
        """Test that invalid Docker Compose structure is handled gracefully."""
        invalid_yaml = """
version: '3.8'
services:
  - invalid structure
"""
        # This is valid YAML but invalid Docker Compose structure
        # The parser should handle it gracefully by returning empty services
        structure = parser_service.parse_compose(invalid_yaml)
        assert len(structure.services) == 0

    def test_parse_non_dict_yaml_raises_error(self, parser_service):
        """Test that non-dictionary YAML raises ValueError."""
        non_dict_yaml = "- item1\n- item2\n- item3"
        
        with pytest.raises(ValueError, match="must be a YAML dictionary"):
            parser_service.parse_compose(non_dict_yaml)

    def test_parse_empty_compose(self, parser_service):
        """Test parsing empty Docker Compose file."""
        empty_compose = """
version: '3.8'
"""
        structure = parser_service.parse_compose(empty_compose)
        
        assert structure.version == '3.8'
        assert len(structure.services) == 0
        assert len(structure.volumes) == 0
        assert len(structure.networks) == 0

    def test_parse_compose_without_version(self, parser_service):
        """Test parsing Docker Compose without version field."""
        compose_yaml = """
services:
  web:
    image: nginx:latest
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert structure.version is None
        assert len(structure.services) == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_compose_with_null_volume_config(self, parser_service):
        """Test parsing volumes with null configuration."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
volumes:
  data:
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.volumes) == 1
        assert structure.volumes[0].name == 'data'

    def test_parse_compose_with_null_network_config(self, parser_service):
        """Test parsing networks with null configuration."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
networks:
  frontend:
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.networks) == 1
        assert structure.networks[0].name == 'frontend'

    def test_parse_compose_with_external_volume(self, parser_service):
        """Test parsing external volumes."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
volumes:
  data:
    external: true
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.volumes) == 1
        assert structure.volumes[0].external is True

    def test_parse_compose_with_complex_port_mapping(self, parser_service):
        """Test parsing complex port mappings with IP."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "127.0.0.1:8080:80"
"""
        structure = parser_service.parse_compose(compose_yaml)
        
        assert len(structure.services) == 1
        assert len(structure.services[0].ports) == 1
        # Should extract the port numbers, ignoring the IP
        port = structure.services[0].ports[0]
        assert port.host == '8080'
        assert port.container == '80'
