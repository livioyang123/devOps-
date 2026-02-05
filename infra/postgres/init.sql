-- Initialize DevOps K8s Platform Database
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create initial tables will be handled by Alembic migrations
-- This file is for any initial data or extensions only

-- Insert initial data if needed
-- Example: INSERT INTO templates (name, description, category, compose_content) VALUES (...);

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE devops_k8s TO devops;