# Layer 1 License Server - Database Models (MySQL/PostgreSQL Compatible)
import os
from typing import Optional, List, Dict
from datetime import datetime
from urllib.parse import urlparse

# ============================================================================
# Database Type Detection and Library Imports
# ============================================================================

# Check if DATABASE_URL is set (Neon/PostgreSQL) or use MySQL
DATABASE_URL = os.getenv("DATABASE_URL")
DB_TYPE = os.getenv("DB_TYPE", "postgresql" if DATABASE_URL else "mysql")

print(f"🔧 Database Type: {DB_TYPE}")

if DB_TYPE == "postgresql":
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import pool as pg_pool
    print("✅ Using PostgreSQL driver")
else:
    import mysql.connector
    from mysql.connector import pooling
    print("✅ Using MySQL driver")

# ============================================================================
# Database Configuration
# ============================================================================

if DB_TYPE == "postgresql":
    # Parse DATABASE_URL for Neon/PostgreSQL
    if DATABASE_URL:
        DB_CONFIG = {"dsn": DATABASE_URL}
        print(f"🔗 Using DATABASE_URL for PostgreSQL connection")
    else:
        # Fallback to individual environment variables
        DB_CONFIG = {
            "host": os.getenv("DB_HOST", "localhost"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "license_server_db"),
            "port": int(os.getenv("DB_PORT", "5432"))
        }
else:
    # MySQL configuration
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "license_server_db"),
    }

# Connection pool
connection_pool = None

# ============================================================================
# Connection Management
# ============================================================================

def get_connection():
    """Get database connection (MySQL or PostgreSQL)."""
    if DB_TYPE == "postgresql":
        if "dsn" in DB_CONFIG:
            return psycopg2.connect(DB_CONFIG["dsn"])
        else:
            return psycopg2.connect(**DB_CONFIG)
    else:
        return mysql.connector.connect(**DB_CONFIG)

def dict_cursor(conn):
    """Get a dictionary cursor for the connection."""
    if DB_TYPE == "postgresql":
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor(dictionary=True)

# ============================================================================
# Schema Initialization
# ============================================================================

def init_database():
    """Initialize database tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("🔧 Initializing database schema...")
    
    # PostgreSQL-compatible schema
    if DB_TYPE == "postgresql":
        schema_sql = """
        CREATE TABLE IF NOT EXISTS admin_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS licenses (
            id SERIAL PRIMARY KEY,
            license_key VARCHAR(50) UNIQUE NOT NULL,
            customer_name VARCHAR(255) NOT NULL,
            company_name VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            expires_at TIMESTAMP NOT NULL,
            max_activations INT DEFAULT 1,
            restricted_fingerprint VARCHAR(255),
            notes TEXT,
            is_blocked BOOLEAN DEFAULT FALSE,
            block_message TEXT,
            created_by VARCHAR(50),
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activations (
            id SERIAL PRIMARY KEY,
            license_key VARCHAR(50) NOT NULL,
            hardware_fingerprint VARCHAR(255) NOT NULL,
            device_name VARCHAR(255),
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_validated TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (license_key) REFERENCES licenses(license_key) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS validation_logs (
            id SERIAL PRIMARY KEY,
            license_key VARCHAR(50),
            hardware_fingerprint VARCHAR(255),
            status VARCHAR(50),
            remote_override BOOLEAN DEFAULT FALSE,
            message TEXT,
            validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create default admin user if not exists (password: admin123)
        INSERT INTO admin_users (username, password_hash)
        VALUES ('admin', 'SHA2:240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9')
        ON CONFLICT (username) DO NOTHING;
        """
    else:
        # MySQL schema
        schema_sql = """
        CREATE TABLE IF NOT EXISTS admin_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS licenses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            license_key VARCHAR(50) UNIQUE NOT NULL,
            customer_name VARCHAR(255) NOT NULL,
            company_name VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            expires_at DATETIME NOT NULL,
            max_activations INT DEFAULT 1,
            restricted_fingerprint VARCHAR(255),
            notes TEXT,
            is_blocked BOOLEAN DEFAULT FALSE,
            block_message TEXT,
            created_by VARCHAR(50),
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            license_key VARCHAR(50) NOT NULL,
            hardware_fingerprint VARCHAR(255) NOT NULL,
            device_name VARCHAR(255),
            activated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_validated DATETIME,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (license_key) REFERENCES licenses(license_key) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS validation_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            license_key VARCHAR(50),
            hardware_fingerprint VARCHAR(255),
            status VARCHAR(50),
            remote_override BOOLEAN DEFAULT FALSE,
            message TEXT,
            validated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Create default admin user if not exists (password: admin123)
        INSERT IGNORE INTO admin_users (username, password_hash)
        VALUES ('admin', 'SHA2:240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9');
        """
    
    # Execute schema
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
                conn.commit()
            except Exception as e:
                # Table might already exist
                print(f"⚠️ Schema statement skipped: {e}")
                pass
    
    cursor.close()
    conn.close()
    print("✅ Database initialized")

# ============================================================================
# Database Helper Functions
# ============================================================================

def get_license(license_key: str) -> Optional[Dict]:
    """Get license by key."""
    conn = get_connection()
    cursor = dict_cursor(conn)
    
    cursor.execute("""
        SELECT * FROM licenses WHERE license_key = %s
    """, (license_key,))
    
    license_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return license_data

def get_all_licenses(limit: int = 100, offset: int = 0, updated_after: Optional[datetime] = None) -> List[Dict]:
    """Get all licenses with pagination and optional time filter."""
    conn = get_connection()
    cursor = dict_cursor(conn)
    
    query = "SELECT * FROM licenses"
    params = []
    
    if updated_after:
        query += " WHERE COALESCE(updated_at, generated_at) > %s"
        params.append(updated_after)
        
    query += " ORDER BY COALESCE(updated_at, generated_at) DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cursor.execute(query, tuple(params))
    
    licenses = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return licenses

def get_activation(license_key: str, hardware_fingerprint: str) -> Optional[Dict]:
    """Get activation by license and hardware fingerprint."""
    conn = get_connection()
    cursor = dict_cursor(conn)
    
    cursor.execute("""
        SELECT * FROM activations 
        WHERE license_key = %s AND hardware_fingerprint = %s AND is_active = TRUE
    """, (license_key, hardware_fingerprint))
    
    activation = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return activation

def get_activations_for_license(license_key: str) -> List[Dict]:
    """Get all activations for a license."""
    conn = get_connection()
    cursor = dict_cursor(conn)
    
    cursor.execute("""
        SELECT * FROM activations 
        WHERE license_key = %s
        ORDER BY activated_at DESC
    """, (license_key,))
    
    activations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return activations

def log_validation(license_key: str, hardware_fingerprint: str, status: str, 
                   remote_override: bool = False, message: str = None):
    """Log a validation attempt."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO validation_logs 
        (license_key, hardware_fingerprint, status, remote_override, message)
        VALUES (%s, %s, %s, %s, %s)
    """, (license_key, hardware_fingerprint, status, remote_override, message))
    
    conn.commit()
    cursor.close()
    conn.close()

def update_last_validated(activation_id: int):
    """Update last validated timestamp for an activation."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == "postgresql":
        cursor.execute("""
            UPDATE activations 
            SET last_validated = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (activation_id,))
    else:
        cursor.execute("""
            UPDATE activations 
            SET last_validated = NOW()
            WHERE id = %s
        """, (activation_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
