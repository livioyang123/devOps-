#!/usr/bin/env python3
"""
Script to run database migrations
This script can be used to apply migrations when the database is available
"""

import os
import sys
import time
import subprocess
from sqlalchemy import create_engine, text
from app.config import settings

def wait_for_db(max_retries=30, delay=2):
    """Wait for database to be available"""
    print("Waiting for database to be available...")
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(settings.database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is available!")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: Database not ready - {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    
    print("Database is not available after maximum retries")
    return False

def run_migrations():
    """Run Alembic migrations"""
    print("Running database migrations...")
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("Migrations completed successfully!")
            print(result.stdout)
            return True
        else:
            print("Migration failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False

def main():
    """Main function"""
    if not wait_for_db():
        sys.exit(1)
    
    if not run_migrations():
        sys.exit(1)
    
    print("Database setup completed successfully!")

if __name__ == "__main__":
    main()