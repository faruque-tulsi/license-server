-- Layer 1 License Server Database Schema
-- MySQL Database for local license management

CREATE DATABASE IF NOT EXISTS license_server_db;
USE license_server_db;

-- Licenses table
CREATE TABLE IF NOT EXISTS licenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(100) UNIQUE NOT NULL,
    customer_name VARCHAR(255),
    company_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    max_activations INT DEFAULT 1,
    restricted_fingerprint VARCHAR(255),
    is_blocked BOOLEAN DEFAULT FALSE,
    block_message TEXT,
    created_by VARCHAR(100) DEFAULT 'admin',
    notes TEXT,
    INDEX idx_license_key (license_key),
    INDEX idx_expires_at (expires_at),
    INDEX idx_is_blocked (is_blocked)
);

-- Activations table
CREATE TABLE IF NOT EXISTS activations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(100) NOT NULL,
    hardware_fingerprint VARCHAR(255) UNIQUE NOT NULL,
    device_name VARCHAR(255),
    activated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_validated DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (license_key) REFERENCES licenses(license_key) ON DELETE CASCADE,
    INDEX idx_hardware_fingerprint (hardware_fingerprint),
    INDEX idx_license_key (license_key),
    INDEX idx_is_active (is_active)
);

-- Validation logs table
CREATE TABLE IF NOT EXISTS validation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(100),
    hardware_fingerprint VARCHAR(255),
    validated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('valid', 'expired', 'blocked', 'not_found', 'hardware_mismatch', 'remote_disabled') DEFAULT 'valid',
    remote_override BOOLEAN DEFAULT FALSE,
    message TEXT,
    INDEX idx_validated_at (validated_at),
    INDEX idx_license_key (license_key)
);

-- Admin users table (simple auth)
CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin (password: admin123)
INSERT IGNORE INTO admin_users (username, password_hash) 
VALUES ('admin', 'SHA2:240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9');

-- Show tables
SHOW TABLES;
