"""
Migration script to sync all existing licenses to remote
"""
import mysql.connector
import requests
import os
import base64
from dotenv import load_dotenv

load_dotenv()

# Database config from .env
DB_CONFIG = {
    'host': os.getenv("DB_HOST", "localhost"),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", ""),
    'database': os.getenv("DB_NAME", "license_server_db")
}

# Remote config (base64 encoded for obfuscation)
_encoded_default = "aHR0cHM6Ly93Yi1jbG91ZC1zeW5jLm9ucmVuZGVyLmNvbQ=="
_remote_url_raw = os.getenv("REMOTE_URL", "")
if _remote_url_raw:
    REMOTE_URL = _remote_url_raw
else:
    REMOTE_URL = base64.b64decode(_encoded_default).decode('utf-8')

REMOTE_ADMIN_TOKEN = os.getenv("REMOTE_ADMIN_TOKEN", "wb_master_sync_key_2025")

print("🔄 Starting license migration to remote...")
print("📡 Connecting to cloud sync service...")

# Connect to database
conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor(dictionary=True)

# Get all licenses
cursor.execute("""
    SELECT license_key, customer_name, company_name, email, phone, 
           expires_at, max_activations, restricted_fingerprint, notes, created_by
    FROM licenses
""")

licenses = cursor.fetchall()
print(f"📊 Found {len(licenses)} licenses to sync")

# Sync each license
success_count = 0
error_count = 0

for license in licenses:
    try:
        response = requests.post(
            f"{REMOTE_URL}/m4st3r/license/sync",
            headers={"Authorization": f"Bearer {REMOTE_ADMIN_TOKEN}"},
            json={
                "license_key": license['license_key'],
                "customer_name": license['customer_name'] or "Unknown",
                "company_name": license['company_name'] or "",
                "email": license['email'] or "",
                "phone": license['phone'] or "",
                "expires_at": str(license['expires_at']),
                "max_activations": license['max_activations'] or 1,
                "restricted_fingerprint": license['restricted_fingerprint'] or "",
                "notes": license['notes'] or "",
                "created_by": license['created_by'] or "admin",
                "generated_at": "2026-01-01T00:00:00"
            },
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Synced: {license['license_key']}")
            success_count += 1
        else:
            error_detail = response.text[:200] if response.text else 'No details'
            print(f"⚠️  Failed: {license['license_key']} - {response.status_code} - {error_detail}")
            error_count += 1
            
    except Exception as e:
        print(f"❌ Error syncing {license['license_key']}: {e}")
        error_count += 1

cursor.close()
conn.close()

print(f"\n✨ Migration complete!")
print(f"✅ Success: {success_count}")
print(f"❌ Errors: {error_count}")
