#!/usr/bin/env python3
"""
Test database connection
"""

import os
import psycopg2
from sqlalchemy import create_engine
from app.config import settings

def test_connection():
    """Test database connection using the configured database URL"""
    
    print(f"Testing connection with URL: {settings.database_url}")
    
    try:
        # Use SQLAlchemy to test the connection
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute("SELECT version()")
            version = result.fetchone()[0]
            print(f"✅ Database connection successful!")
            print(f"PostgreSQL version: {version}")
            
            # Test if our tables exist
            result = conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = result.fetchall()
            
            if tables:
                print(f"✅ Found {len(tables)} tables:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("⚠️  No tables found. Run migrations to create tables.")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        
        # Try with direct psycopg2 connection using IPv4 explicitly
        try:
            print("\nTrying direct psycopg2 connection with IPv4...")
            conn = psycopg2.connect(
                host="127.0.0.1",  # Force IPv4
                port=5432,
                database="devops_k8s",
                user="devops",
                password="devops123"
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            result = cursor.fetchone()
            print(f"✅ Direct IPv4 connection successful: {result[0]}")
            cursor.close()
            conn.close()
            return True
        except Exception as e2:
            print(f"❌ Direct IPv4 connection also failed: {e2}")
            
            # Try without password (trust authentication)
            try:
                print("\nTrying connection without password (trust auth)...")
                conn = psycopg2.connect(
                    host="127.0.0.1",
                    port=5432,
                    database="devops_k8s",
                    user="devops"
                    # No password
                )
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                result = cursor.fetchone()
                print(f"✅ Trust authentication successful: {result[0]}")
                cursor.close()
                conn.close()
                return True
            except Exception as e3:
                print(f"❌ Trust authentication failed: {e3}")
                return False

if __name__ == "__main__":
    test_connection()