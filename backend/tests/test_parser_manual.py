"""
Manual test script to demonstrate Parser Service functionality.
Run this to see the parser in action with various Docker Compose examples.
"""
from app.services.parser import ParserService
import json


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def main():
    parser = ParserService()
    
    # Example 1: Valid Docker Compose
    print_section("Example 1: Valid Docker Compose with Multiple Services")
    
    compose1 = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    environment:
      NODE_ENV: production
      DEBUG: "false"
    depends_on:
      - db
    volumes:
      - ./html:/usr/share/nginx/html
    networks:
      - frontend
  
  db:
    image: postgres:13
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    volumes:
      - db_data:/var/lib/postgresql/data
    networks:
      - backend

volumes:
  db_data:
    driver: local

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
"""
    
    validation = parser.validate_yaml(compose1)
    print(f"YAML Valid: {validation.valid}")
    
    if validation.valid:
        structure = parser.parse_compose(compose1)
        print(f"\nVersion: {structure.version}")
        print(f"Services: {len(structure.services)}")
        for service in structure.services:
            print(f"  - {service.name}: {service.image}")
            print(f"    Ports: {len(service.ports)}")
            print(f"    Environment vars: {len(service.environment)}")
            print(f"    Depends on: {service.depends_on}")
        
        print(f"\nVolumes: {len(structure.volumes)}")
        for volume in structure.volumes:
            print(f"  - {volume.name} (driver: {volume.driver})")
        
        print(f"\nNetworks: {len(structure.networks)}")
        for network in structure.networks:
            print(f"  - {network.name} (driver: {network.driver})")
    
    # Example 2: Invalid YAML
    print_section("Example 2: Invalid YAML Syntax")
    
    compose2 = """
version: '3.8'
services:
  web:
    image: nginx:latest
  - invalid indentation
"""
    
    validation = parser.validate_yaml(compose2)
    print(f"YAML Valid: {validation.valid}")
    
    if not validation.valid:
        print("\nValidation Errors:")
        for error in validation.errors:
            print(f"  Line {error.line}, Column {error.column}: {error.message}")
            print(f"  Error Type: {error.error_type}")
    
    # Example 3: WordPress Stack
    print_section("Example 3: WordPress Stack")
    
    compose3 = """
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
    
    structure = parser.parse_compose(compose3)
    print(f"Services: {len(structure.services)}")
    
    wordpress = next(s for s in structure.services if s.name == 'wordpress')
    print(f"\nWordPress Service:")
    print(f"  Image: {wordpress.image}")
    print(f"  Ports: {[f'{p.host}:{p.container}' for p in wordpress.ports]}")
    print(f"  Environment: {len(wordpress.environment)} variables")
    print(f"  Depends on: {wordpress.depends_on}")
    print(f"  Volumes: {wordpress.volumes}")
    
    db = next(s for s in structure.services if s.name == 'db')
    print(f"\nDatabase Service:")
    print(f"  Image: {db.image}")
    print(f"  Environment: {len(db.environment)} variables")
    print(f"  Volumes: {db.volumes}")
    
    print(f"\nTotal Volumes: {len(structure.volumes)}")
    for vol in structure.volumes:
        print(f"  - {vol.name}")
    
    # Example 4: Empty Compose
    print_section("Example 4: Empty Docker Compose")
    
    compose4 = """
version: '3.8'
"""
    
    structure = parser.parse_compose(compose4)
    print(f"Version: {structure.version}")
    print(f"Services: {len(structure.services)}")
    print(f"Volumes: {len(structure.volumes)}")
    print(f"Networks: {len(structure.networks)}")
    print("\nThis is a valid but empty Docker Compose file.")
    
    print_section("All Examples Completed Successfully!")


if __name__ == "__main__":
    main()
