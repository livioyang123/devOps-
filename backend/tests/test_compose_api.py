"""
Integration tests for Compose API endpoints.
Tests the upload, parse, and validate endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestComposeUploadEndpoint:
    """Test /api/compose/upload endpoint."""

    def test_upload_valid_compose(self):
        """Test uploading a valid Docker Compose file."""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    environment:
      NODE_ENV: production
"""
        response = client.post(
            "/api/compose/upload",
            json={"content": compose_content}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check validation result
        assert data["validation"]["valid"] is True
        assert len(data["validation"]["errors"]) == 0
        
        # Check structure
        assert data["structure"]["version"] == "3.8"
        assert len(data["structure"]["services"]) == 1
        assert data["structure"]["services"][0]["name"] == "web"
        assert data["structure"]["services"][0]["image"] == "nginx:latest"
        assert len(data["structure"]["services"][0]["ports"]) == 1
        assert data["structure"]["services"][0]["environment"]["NODE_ENV"] == "production"

    def test_upload_invalid_yaml(self):
        """Test uploading invalid YAML."""
        invalid_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
  - invalid indentation
"""
        response = client.post(
            "/api/compose/upload",
            json={"content": invalid_content}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return validation errors
        assert data["validation"]["valid"] is False
        assert len(data["validation"]["errors"]) > 0
        assert data["validation"]["errors"][0]["line"] is not None

    def test_upload_empty_compose(self):
        """Test uploading empty Docker Compose."""
        empty_content = """
version: '3.8'
"""
        response = client.post(
            "/api/compose/upload",
            json={"content": empty_content}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["validation"]["valid"] is True
        assert data["structure"]["version"] == "3.8"
        assert len(data["structure"]["services"]) == 0


class TestComposeParseEndpoint:
    """Test /api/compose/parse endpoint."""

    def test_parse_valid_compose(self):
        """Test parsing a valid Docker Compose file."""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
  db:
    image: postgres:13
volumes:
  data:
    driver: local
networks:
  frontend:
    driver: bridge
"""
        response = client.post(
            "/api/compose/parse",
            json={"content": compose_content}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["version"] == "3.8"
        assert len(data["services"]) == 2
        assert len(data["volumes"]) == 1
        assert len(data["networks"]) == 1

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML returns 400."""
        invalid_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
  - invalid indentation
"""
        response = client.post(
            "/api/compose/parse",
            json={"content": invalid_content}
        )
        
        # Should return 400 for invalid YAML
        assert response.status_code == 400

    def test_parse_non_dict_yaml(self):
        """Test parsing non-dictionary YAML returns 400."""
        non_dict_content = "- item1\n- item2"
        
        response = client.post(
            "/api/compose/parse",
            json={"content": non_dict_content}
        )
        
        assert response.status_code == 400


class TestComposeValidateEndpoint:
    """Test /api/compose/validate endpoint."""

    def test_validate_valid_yaml(self):
        """Test validating valid YAML."""
        valid_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
"""
        response = client.post(
            "/api/compose/validate",
            json={"content": valid_content}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert len(data["errors"]) == 0

    def test_validate_invalid_yaml(self):
        """Test validating invalid YAML."""
        invalid_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
  - invalid
"""
        response = client.post(
            "/api/compose/validate",
            json={"content": invalid_content}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert data["errors"][0]["message"] is not None

    def test_validate_yaml_with_tabs(self):
        """Test validating YAML with tabs (invalid in YAML)."""
        yaml_with_tabs = "version: '3.8'\n\tservices:\n\t\tweb:\n\t\t\timage: nginx"
        
        response = client.post(
            "/api/compose/validate",
            json={"content": yaml_with_tabs}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert len(data["errors"]) > 0


class TestComplexComposeScenarios:
    """Test complex Docker Compose scenarios."""

    def test_parse_wordpress_stack(self):
        """Test parsing a WordPress stack."""
        wordpress_compose = """
version: '3.8'
services:
  wordpress:
    image: wordpress:latest
    ports:
      - "8080:80"
    environment:
      WORDPRESS_DB_HOST: db
      WORDPRESS_DB_USER: wordpress
      WORDPRESS_DB_PASSWORD: wordpress
      WORDPRESS_DB_NAME: wordpress
    depends_on:
      - db
    volumes:
      - wordpress_data:/var/www/html
  
  db:
    image: mysql:5.7
    environment:
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wordpress
      MYSQL_PASSWORD: wordpress
      MYSQL_ROOT_PASSWORD: rootpassword
    volumes:
      - db_data:/var/lib/mysql

volumes:
  wordpress_data:
  db_data:
"""
        response = client.post(
            "/api/compose/parse",
            json={"content": wordpress_compose}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["services"]) == 2
        assert len(data["volumes"]) == 2
        
        # Check WordPress service
        wordpress = next(s for s in data["services"] if s["name"] == "wordpress")
        assert len(wordpress["depends_on"]) == 1
        assert "db" in wordpress["depends_on"]
        assert len(wordpress["environment"]) == 4
        
        # Check DB service
        db = next(s for s in data["services"] if s["name"] == "db")
        assert len(db["environment"]) == 4

    def test_parse_microservices_stack(self):
        """Test parsing a microservices stack with multiple networks."""
        microservices_compose = """
version: '3.8'
services:
  frontend:
    image: frontend:latest
    ports:
      - "3000:3000"
    networks:
      - frontend_net
    depends_on:
      - api
  
  api:
    image: api:latest
    ports:
      - "8000:8000"
    networks:
      - frontend_net
      - backend_net
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    networks:
      - backend_net
    environment:
      POSTGRES_PASSWORD: password
  
  redis:
    image: redis:alpine
    networks:
      - backend_net

networks:
  frontend_net:
    driver: bridge
  backend_net:
    driver: bridge
"""
        response = client.post(
            "/api/compose/parse",
            json={"content": microservices_compose}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["services"]) == 4
        assert len(data["networks"]) == 2
        
        # Check API service has both networks
        api = next(s for s in data["services"] if s["name"] == "api")
        assert len(api["networks"]) == 2
        assert "frontend_net" in api["networks"]
        assert "backend_net" in api["networks"]
