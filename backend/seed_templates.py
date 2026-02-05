"""
Seed script to populate the database with pre-built Docker Compose templates
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import Base, Template

# Template definitions
TEMPLATES = [
    {
        "name": "WordPress",
        "description": "WordPress with MySQL database - A popular content management system",
        "category": "web",
        "compose_content": """version: '3.8'

services:
  wordpress:
    image: wordpress:latest
    ports:
      - "8080:80"
    environment:
      WORDPRESS_DB_HOST: db
      WORDPRESS_DB_USER: wordpress
      WORDPRESS_DB_PASSWORD: {{DB_PASSWORD}}
      WORDPRESS_DB_NAME: wordpress
    volumes:
      - wordpress_data:/var/www/html
    depends_on:
      - db
    networks:
      - wordpress_network

  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wordpress
      MYSQL_PASSWORD: {{DB_PASSWORD}}
      MYSQL_ROOT_PASSWORD: {{DB_ROOT_PASSWORD}}
    volumes:
      - db_data:/var/lib/mysql
    networks:
      - wordpress_network

volumes:
  wordpress_data:
  db_data:

networks:
  wordpress_network:
    driver: bridge
""",
        "required_params": {
            "parameters": ["DB_PASSWORD", "DB_ROOT_PASSWORD"],
            "descriptions": {
                "DB_PASSWORD": "Password for WordPress database user",
                "DB_ROOT_PASSWORD": "Root password for MySQL database"
            }
        }
    },
    {
        "name": "LAMP Stack",
        "description": "Linux, Apache, MySQL, PHP stack for web applications",
        "category": "web",
        "compose_content": """version: '3.8'

services:
  apache-php:
    image: php:8.1-apache
    ports:
      - "8080:80"
    volumes:
      - ./app:/var/www/html
    environment:
      MYSQL_HOST: mysql
      MYSQL_DATABASE: {{DB_NAME}}
      MYSQL_USER: {{DB_USER}}
      MYSQL_PASSWORD: {{DB_PASSWORD}}
    depends_on:
      - mysql
    networks:
      - lamp_network

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: {{DB_ROOT_PASSWORD}}
      MYSQL_DATABASE: {{DB_NAME}}
      MYSQL_USER: {{DB_USER}}
      MYSQL_PASSWORD: {{DB_PASSWORD}}
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - lamp_network

  phpmyadmin:
    image: phpmyadmin:latest
    ports:
      - "8081:80"
    environment:
      PMA_HOST: mysql
      PMA_USER: {{DB_USER}}
      PMA_PASSWORD: {{DB_PASSWORD}}
    depends_on:
      - mysql
    networks:
      - lamp_network

volumes:
  mysql_data:

networks:
  lamp_network:
    driver: bridge
""",
        "required_params": {
            "parameters": ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_ROOT_PASSWORD"],
            "descriptions": {
                "DB_NAME": "Name of the MySQL database",
                "DB_USER": "MySQL user name",
                "DB_PASSWORD": "MySQL user password",
                "DB_ROOT_PASSWORD": "MySQL root password"
            }
        }
    },
    {
        "name": "MEAN Stack",
        "description": "MongoDB, Express, Angular, Node.js stack for modern web applications",
        "category": "web",
        "compose_content": """version: '3.8'

services:
  mongodb:
    image: mongo:6.0
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: {{MONGO_USER}}
      MONGO_INITDB_ROOT_PASSWORD: {{MONGO_PASSWORD}}
      MONGO_INITDB_DATABASE: {{DB_NAME}}
    volumes:
      - mongodb_data:/data/db
    networks:
      - mean_network

  backend:
    image: node:18-alpine
    working_dir: /app
    volumes:
      - ./backend:/app
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: production
      MONGODB_URI: mongodb://{{MONGO_USER}}:{{MONGO_PASSWORD}}@mongodb:27017/{{DB_NAME}}?authSource=admin
      PORT: 3000
    command: sh -c "npm install && npm start"
    depends_on:
      - mongodb
    networks:
      - mean_network

  frontend:
    image: node:18-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app
    ports:
      - "4200:4200"
    environment:
      NODE_ENV: production
      API_URL: http://backend:3000
    command: sh -c "npm install && npm start"
    depends_on:
      - backend
    networks:
      - mean_network

volumes:
  mongodb_data:

networks:
  mean_network:
    driver: bridge
""",
        "required_params": {
            "parameters": ["MONGO_USER", "MONGO_PASSWORD", "DB_NAME"],
            "descriptions": {
                "MONGO_USER": "MongoDB admin username",
                "MONGO_PASSWORD": "MongoDB admin password",
                "DB_NAME": "Name of the MongoDB database"
            }
        }
    },
    {
        "name": "PostgreSQL with Redis",
        "description": "PostgreSQL database with Redis cache - Perfect for data-intensive applications",
        "category": "database",
        "compose_content": """version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: {{DB_NAME}}
      POSTGRES_USER: {{DB_USER}}
      POSTGRES_PASSWORD: {{DB_PASSWORD}}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - db_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {{DB_USER}}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass {{REDIS_PASSWORD}}
    volumes:
      - redis_data:/data
    networks:
      - db_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgadmin:
    image: dpage/pgadmin4:latest
    ports:
      - "5050:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: {{ADMIN_EMAIL}}
      PGADMIN_DEFAULT_PASSWORD: {{ADMIN_PASSWORD}}
    depends_on:
      - postgres
    networks:
      - db_network

volumes:
  postgres_data:
  redis_data:

networks:
  db_network:
    driver: bridge
""",
        "required_params": {
            "parameters": ["DB_NAME", "DB_USER", "DB_PASSWORD", "REDIS_PASSWORD", "ADMIN_EMAIL", "ADMIN_PASSWORD"],
            "descriptions": {
                "DB_NAME": "PostgreSQL database name",
                "DB_USER": "PostgreSQL user name",
                "DB_PASSWORD": "PostgreSQL user password",
                "REDIS_PASSWORD": "Redis authentication password",
                "ADMIN_EMAIL": "PgAdmin admin email",
                "ADMIN_PASSWORD": "PgAdmin admin password"
            }
        }
    }
]


def seed_templates():
    """Seed the database with pre-built templates"""
    db = SessionLocal()
    
    try:
        # Check if templates already exist
        existing_count = db.query(Template).count()
        
        if existing_count > 0:
            print(f"Database already contains {existing_count} templates. Skipping seed.")
            print("To re-seed, delete existing templates first.")
            return
        
        # Create templates
        for template_data in TEMPLATES:
            template = Template(
                id=uuid.uuid4(),
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                compose_content=template_data["compose_content"],
                required_params=template_data["required_params"],
                is_public=True
            )
            db.add(template)
            print(f"Created template: {template_data['name']}")
        
        db.commit()
        print(f"\nSuccessfully seeded {len(TEMPLATES)} templates!")
        
        # Display summary
        print("\nTemplate Summary:")
        for template_data in TEMPLATES:
            print(f"  - {template_data['name']} ({template_data['category']})")
            if template_data.get('required_params'):
                params = template_data['required_params'].get('parameters', [])
                print(f"    Required parameters: {', '.join(params)}")
    
    except Exception as e:
        print(f"Error seeding templates: {str(e)}")
        db.rollback()
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding templates...")
    seed_templates()
