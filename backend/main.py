import os
import secrets
import hashlib
import requests
import base64
import asyncio 
import functools # Added for run_in_executor
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

from models import *
from database import (
    init_database, get_connection, dict_cursor, get_license, get_all_licenses,
    get_activation, get_activations_for_license, log_validation,
    update_last_validated
)

# Create FastAPI app
app = FastAPI(title="License Server - Layer 1", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_encoded_default = "aHR0cHM6Ly93Yi1jbG91ZC1zeW5jLm9ucmVuZGVyLmNvbQ=="
_remote_url_raw = os.getenv("REMOTE_URL", "")
if _remote_url_raw:
    # If URL is provided in env, use it directly
    REMOTE_URL = _remote_url_raw
else:
    # Decode from base64
    REMOTE_URL = base64.b64decode(_encoded_default).decode('utf-8')

# Remote Admin Token (for syncing)
REMOTE_ADMIN_TOKEN = os.getenv("REMOTE_ADMIN_TOKEN", "REPLACE_WITH_REAL_TOKEN_IN_ENV")

async def push_all_licenses_periodically():
    """Background task to push all licenses to remote every 15 minutes."""
    # Initial delay to let server start up completely
    await asyncio.sleep(5)
    
    while True:
        if REMOTE_ADMIN_TOKEN == 'REPLACE_WITH_REAL_TOKEN_IN_ENV':
            print("⏳ Remote sync not configured. Waiting 60s...")
            await asyncio.sleep(60)
            continue

        print("🔄 Starting scheduled full sync to remote...")
        loop = asyncio.get_event_loop()
        
        try:
            # 1. Fetch all local licenses (Run DB call in executor)
            # Use partial to pass arguments to the blocking function
            licenses = await loop.run_in_executor(
                None, 
                functools.partial(get_all_licenses, limit=1000)
            )
            
            success_count = 0
            for lic in licenses:
                try:
                    # Prepare payload
                    payload = lic.copy()
                    if isinstance(payload.get('expires_at'), datetime):
                        payload['expires_at'] = payload['expires_at'].isoformat()
                    if isinstance(payload.get('generated_at'), datetime):
                        payload['generated_at'] = payload['generated_at'].isoformat()
                    if isinstance(payload.get('updated_at'), datetime):
                        payload['updated_at'] = payload['updated_at'].isoformat()
                    
                    # Push (Run Network call in executor)
                    def push_request():
                        return requests.post(
                            f"{REMOTE_URL}/m4st3r/license/sync",
                            json=payload,
                            headers={"Authorization": f"Bearer {REMOTE_ADMIN_TOKEN}"},
                            timeout=60.0 # Keep long timeout for cold starts
                        )
                    
                    response = await loop.run_in_executor(None, push_request)
                    
                    if response.status_code == 200:
                        success_count += 1
                except Exception as ex:
                    print(f"⚠️ Failed to push license {lic.get('license_key')}: {ex}")
                
                # Small yield not strictly needed with executor but good practice
                await asyncio.sleep(0.01)
                
            print(f"✅ Scheduled sync complete: Pushed {success_count}/{len(licenses)} licenses.")
            
        except Exception as e:
            print(f"❌ Scheduled sync error: {e}")
        
        # Wait 15 minutes (900 seconds)
        await asyncio.sleep(900)

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_database()
    print(f"✅ License Server ready")
    print(f"🔗 Remote sync: {'Enabled' if REMOTE_ADMIN_TOKEN != 'REPLACE_WITH_REAL_TOKEN_IN_ENV' else 'Disabled'}")
    
    # Start background sync task
    if REMOTE_ADMIN_TOKEN != "REPLACE_WITH_REAL_TOKEN_IN_ENV":
        print(f"🔗 Cloud sync: Enabled. Starting background pusher...")
        asyncio.create_task(push_all_licenses_periodically())

# Simple admin authentication (stored in memory for demo)
_admin_tokens = {}

def verify_admin(authorization: Optional[str] = Header(None)):
    """Verify admin authentication."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    if token not in _admin_tokens:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return _admin_tokens[token]

# ============================================================================
# SYNC HELPERS
# ============================================================================

async def sync_license_to_remote(license_data: dict):
    """Push new license to remote registry."""
    if REMOTE_ADMIN_TOKEN == 'REPLACE_WITH_REAL_TOKEN_IN_ENV':
        print(f"⚠️ Skipping remote sync: Token not configured")
        return

    try:
        # Format dates for JSON
        payload = license_data.copy()
        payload['expires_at'] = payload['expires_at'].isoformat() if isinstance(payload['expires_at'], datetime) else payload['expires_at']
        payload['generated_at'] = str(datetime.now()) # sending current time as generated_at is not in input payload

        print(f"🔄 Syncing license {payload['license_key']} to remote...")
        response = requests.post(
            f"{REMOTE_URL}/m4st3r/license/sync",
            json=payload,
            headers={"Authorization": f"Bearer {REMOTE_ADMIN_TOKEN}"},
            timeout=60.0
        )
        
        if response.status_code == 200:
            print(f"✅ License synced successfully")
        else:
            print(f"❌ improved Sync failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Sync error: {e}")

async def fetch_license_from_remote(license_key: str):
    """Fetch license details from remote registry."""
    try:
        print(f"🔍 Searching for license {license_key} remotely...")
        response = requests.get(
            f"{REMOTE_URL}/sys/license/{license_key}",
            timeout=60.0
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"⚠️ Remote fetch error: {e}")
        return None

def import_license_to_local(license_data: dict):
    """Import a license fetched from remote into local DB."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Convert iso format strings back to datetime if needed, 
        # but MySQL connector often handles strings fine.
        
        cursor.execute("""
            INSERT INTO licenses 
            (license_key, customer_name, company_name, email, phone, 
             expires_at, max_activations, restricted_fingerprint, notes, created_by, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            customer_name=VALUES(customer_name), expires_at=VALUES(expires_at)
        """, (
            license_data['license_key'], 
            license_data['customer_name'], 
            license_data.get('company_name'),
            license_data.get('email'), 
            license_data.get('phone'), 
            license_data['expires_at'],
            license_data['max_activations'], 
            license_data['restricted_fingerprint'], 
            license_data.get('notes'), 
            license_data.get('created_by', 'system_sync'),
            license_data.get('generated_at', datetime.now())
        ))
        
        conn.commit()
        print(f"✅ Imported license {license_data['license_key']} to local DB")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.post("/admin/login")
async def admin_login(payload: AdminLogin):
    """Admin login."""
    print(f"🔐 Login attempt for user: {payload.username}")
    conn = get_connection()
    cursor = dict_cursor(conn)
    
    cursor.execute("SELECT * FROM admin_users WHERE username = %s", (payload.username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        print(f"❌ User not found: {payload.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Simple password check
    password_hash = "SHA2:" + hashlib.sha256(payload.password.encode()).hexdigest()
    db_hash = str(user['password_hash']).strip()
    
    print(f"🔍 DB Hash: '{db_hash}' (len: {len(db_hash)})")
    print(f"🔍 Calc Hash: '{password_hash}' (len: {len(password_hash)})")
    
    if db_hash != password_hash:
        print(f"❌ Password mismatch for: {payload.username}")
        # Detailed comparison check
        if db_hash.lower() == password_hash.lower():
            print("💡 Note: Case mismatch detected!")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    print(f"✅ Login successful: {payload.username}")
    # Generate token
    token = secrets.token_urlsafe(32)
    _admin_tokens[token] = user['username']
    
    return {"token": token, "username": user['username']}

@app.post("/admin/generate")
async def generate_license(payload: LicenseCreate, admin=Depends(verify_admin)):
    """Generate a new license key."""
    import uuid
    
    # Generate unique license key
    license_key = f"WB-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
    
    conn = get_connection()
    cursor = conn.cursor()
    
    license_id = None
    try:
        cursor.execute("""
            INSERT INTO licenses 
            (license_key, customer_name, company_name, email, phone, 
             expires_at, max_activations, restricted_fingerprint, notes, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            license_key, payload.customer_name, payload.company_name,
            payload.email, payload.phone, payload.expires_at,
            payload.max_activations, payload.restricted_fingerprint, payload.notes, admin
        ))
        
        conn.commit()
        license_id = cursor.lastrowid
        
    finally:
        cursor.close()
        conn.close()

    # SYNC TO REMOTE
    sync_data = payload.dict()
    sync_data['license_key'] = license_key
    sync_data['created_by'] = admin
    await sync_license_to_remote(sync_data)
    
    return {
        "success": True,
        "license_key": license_key,
        "id": license_id,
        "message": "License generated successfully"
    }

@app.get("/admin/licenses")
async def list_licenses(
    limit: int = 100,
    offset: int = 0,
    updated_after: Optional[datetime] = None,
    admin=Depends(verify_admin)
):
    """List all licenses."""
    licenses = get_all_licenses(limit, offset, updated_after)
    
    # Get activation count for each license
    for license in licenses:
        activations = get_activations_for_license(license['license_key'])
        license['activation_count'] = len([a for a in activations if a['is_active']])
    
    return {"licenses": licenses, "total": len(licenses)}

@app.get("/admin/licenses/{license_key}")
async def get_license_details(license_key: str, admin=Depends(verify_admin)):
    """Get license details including activations."""
    license = get_license(license_key)
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    
    activations = get_activations_for_license(license_key)
    
    return {
        "license": license,
        "activations": activations
    }

@app.post("/admin/block")
async def block_license(payload: BlockRequest, admin=Depends(verify_admin)):
    """Block a license."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE licenses 
        SET is_blocked = TRUE, block_message = %s
        WHERE license_key = %s
    """, (payload.message, payload.license_key))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"success": True, "message": "License blocked"}

@app.post("/admin/unblock")
async def unblock_license(license_key: str, admin=Depends(verify_admin)):
    """Unblock a license."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE licenses 
        SET is_blocked = FALSE, block_message = NULL
        WHERE license_key = %s
    """, (license_key,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"success": True, "message": "License unblocked"}

@app.post("/admin/extend")
async def extend_license(payload: ExtendRequest, admin=Depends(verify_admin)):
    """Extend license expiry date."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE licenses 
        SET expires_at = %s
        WHERE license_key = %s
    """, (payload.new_expiry, payload.license_key))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Sync update to remote
    try:
        requests.patch(
            f"{REMOTE_URL}/m4st3r/central/licenses/{payload.license_key}",
            headers={"Authorization": f"Bearer {REMOTE_ADMIN_TOKEN}"},
            json={"expires_at": payload.new_expiry},
            timeout=60.0
        )
        print(f"✅ License expiry synced remotely: {payload.license_key}")
    except Exception as e:
        print(f"⚠️ Failed to sync expiry remotely: {e}")
    
    return {"success": True, "message": "License expiry extended"}

@app.delete("/admin/licenses/{license_key}")
async def delete_license(license_key: str, admin=Depends(verify_admin)):
    """Delete a license and all its activations."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Delete activations first (foreign key constraint)
        cursor.execute("DELETE FROM activations WHERE license_key = %s", (license_key,))
        
        # Delete license
        cursor.execute("DELETE FROM licenses WHERE license_key = %s", (license_key,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="License not found")
        
        conn.commit()
        
        # Sync deletion to remote
        try:
            requests.delete(
                f"{REMOTE_URL}/m4st3r/central/licenses/{license_key}",
                headers={"Authorization": f"Bearer {REMOTE_ADMIN_TOKEN}"},
                timeout=60.0
            )
            print(f"✅ License deletion synced remotely: {license_key}")
        except Exception as e:
            print(f"⚠️ Failed to sync deletion remotely: {e}")
        
    finally:
        cursor.close()
        conn.close()
    
    return {"success": True, "message": "License deleted successfully"}

@app.get("/admin/activations")
async def list_activations(admin=Depends(verify_admin)):
    """List all activations."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.*, l.customer_name, l.company_name, l.expires_at
        FROM activations a
        JOIN licenses l ON a.license_key = l.license_key
        ORDER BY a.activated_at DESC
        LIMIT 100
    """)
    
    activations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return {"activations": activations}

@app.delete("/admin/activation/{activation_id}")
async def deactivate_device(activation_id: int, admin=Depends(verify_admin)):
    """Deactivate a specific device."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE activations 
        SET is_active = FALSE
        WHERE id = %s
    """, (activation_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"success": True, "message": "Device deactivated"}

@app.get("/admin/stats")
async def get_stats(admin=Depends(verify_admin)):
    """Get license statistics."""
    conn = get_connection()
    cursor = dict_cursor(conn)
    
    # Total licenses
    cursor.execute("SELECT COUNT(*) as total FROM licenses")
    total = cursor.fetchone()['total']
    
    # Active licenses (not expired, not blocked)
    cursor.execute("""
        SELECT COUNT(*) as active 
        FROM licenses 
        WHERE expires_at > NOW() AND is_blocked = FALSE
    """)
    active = cursor.fetchone()['active']
    
    # Expired licenses
    cursor.execute("""
        SELECT COUNT(*) as expired 
        FROM licenses 
        WHERE expires_at <= NOW()
    """)
    expired = cursor.fetchone()['expired']
    
    # Blocked licenses
    cursor.execute("SELECT COUNT(*) as blocked FROM licenses WHERE is_blocked = TRUE")
    blocked = cursor.fetchone()['blocked']
    
    # Total activations
    cursor.execute("SELECT COUNT(*) as total FROM activations WHERE is_active = TRUE")
    activations = cursor.fetchone()['total']
    
    cursor.close()
    conn.close()
    
    return {
        "total_licenses": total,
        "active_licenses": active,
        "expired_licenses": expired,
        "blocked_licenses": blocked,
        "total_activations": activations
    }

# ============================================================================
# CLIENT ENDPOINTS
# ============================================================================

async def check_remote_override(license_key: str) -> dict:
    """Check remote server for override."""
    try:
        response = requests.post(
            f"{REMOTE_URL}/sys/validate",
            params={"license_key": license_key},
            timeout=10.0
        )
        data = response.json()
        print(f"📡 Remote Validation for {license_key}: {data}")
        return data
    except Exception as e:
        print(f"⚠️ Remote check failed: {e}")
        return {"allowed": True}  # Fail-open if remote is unreachable

@app.post("/activate")
async def activate_license(payload: ActivateRequest):
    """Activate a license on a device."""
    # 1. Check if license exists locally
    license = get_license(payload.license_key)
    
    # 1a. If not found locally, try to fetch from remote
    if not license:
        print(f"License {payload.license_key} not found locally. Checking remote...")
        remote_license = await fetch_license_from_remote(payload.license_key)
        
        if remote_license:
            import_license_to_local(remote_license)
            license = get_license(payload.license_key) # Re-fetch
        else:
             print("License not found remotely either.")
    
    if not license:
        raise HTTPException(status_code=404, detail="Invalid license key. Please check and try again.")
    
    # 2. Check remote override
    remote_status = await check_remote_override(payload.license_key)
    if not remote_status.get('allowed', True):
        log_validation(
            payload.license_key, payload.hardware_fingerprint,
            'remote_disabled', True, remote_status.get('message')
        )
        raise HTTPException(status_code=403, detail=remote_status.get('message', 'License disabled by administrator'))
    
    # 3. Check Hardware Binding (MANDATORY)
    if not license.get('restricted_fingerprint'):
        # This shouldn't happen with new licenses, but for safety:
        log_validation(payload.license_key, payload.hardware_fingerprint, 'not_implemented')
        raise HTTPException(status_code=403, detail="License is missing hardware binding secure data.")
        
    if license['restricted_fingerprint'] != payload.hardware_fingerprint:
        log_validation(
            payload.license_key, payload.hardware_fingerprint, 
            'hardware_mismatch', False, 
            f"License is strictly bound to machine {license['restricted_fingerprint']}"
        )
        raise HTTPException(status_code=403, detail="Activation Failed: This license is already bound to a different machine.")

    # 4. Check if blocked
    if license['is_blocked']:
        log_validation(payload.license_key, payload.hardware_fingerprint, 'blocked')
        raise HTTPException(status_code=403, detail=license['block_message'] or 'License is blocked')
    
    # 4. Check if expired
    if license['expires_at'] < datetime.now():
        log_validation(payload.license_key, payload.hardware_fingerprint, 'expired')
        raise HTTPException(status_code=403, detail='License has expired')
    
    # 5. Check activation count
    existing_activations = get_activations_for_license(payload.license_key)
    active_count = len([a for a in existing_activations if a['is_active']])
    
    # Check if already activated on this device
    existing = get_activation(payload.license_key, payload.hardware_fingerprint)
    if existing:
        log_validation(payload.license_key, payload.hardware_fingerprint, 'valid')
        return {
            "success": True,
            "message": "Already activated on this device",
            "expires_at": license['expires_at']
        }
    
    # Check max activations
    if active_count >= license['max_activations']:
        log_validation(payload.license_key, payload.hardware_fingerprint, 'hardware_mismatch')
        raise HTTPException(status_code=403, detail=f'Maximum activations ({license["max_activations"]}) reached')
    
    # 6. Activate
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO activations 
        (license_key, hardware_fingerprint, device_name)
        VALUES (%s, %s, %s)
    """, (payload.license_key, payload.hardware_fingerprint, payload.device_name))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log_validation(payload.license_key, payload.hardware_fingerprint, 'valid')
    
    return {
        "success": True,
        "message": "License activated successfully",
        "expires_at": license['expires_at']
    }

@app.post("/validate")
async def validate_license(payload: ValidateRequest):
    """Validate a license."""
    # 1. Check remote override
    remote_status = await check_remote_override(payload.license_key)
    if not remote_status.get('allowed', True):
        log_validation(
            payload.license_key, payload.hardware_fingerprint,
            'remote_disabled', True, remote_status.get('message')
        )
        return {
            "valid": False,
            "is_blocked": True,
            "reason": "remote_disabled",
            "message": remote_status.get('message', 'License disabled by administrator')
        }
    
    # 2. Check license exists
    license = get_license(payload.license_key)
    
    # 2a. Attempt fetch if missing (optional for validate, but good for self-healing)
    if not license:
         remote_license = await fetch_license_from_remote(payload.license_key)
         if remote_license:
            import_license_to_local(remote_license)
            license = get_license(payload.license_key)

    if not license:
        log_validation(payload.license_key, payload.hardware_fingerprint, 'not_found')
        raise HTTPException(
            status_code=404,
            detail="License not found or has been deleted"
        )
    
    # 3. Check if blocked
    if license['is_blocked']:
        log_validation(payload.license_key, payload.hardware_fingerprint, 'blocked')
        return {
            "valid": False,
            "is_blocked": True,
            "reason": "blocked",
            "message": license['block_message'] or 'License is blocked'
        }
    
    # 4. Check if expired
    if license['expires_at'] < datetime.now():
        log_validation(payload.license_key, payload.hardware_fingerprint, 'expired')
        return {
            "valid": False,
            "reason": "expired",
            "message": "License has expired",
            "expired_at": license['expires_at']
        }
    
    # 5. Check activation
    activation = get_activation(payload.license_key, payload.hardware_fingerprint)
    if not activation:
        log_validation(payload.license_key, payload.hardware_fingerprint, 'hardware_mismatch')
        return {
            "valid": False,
            "reason": "not_activated",
            "message": "License not activated on this device"
        }
    
    # 6. Update validation timestamp
    update_last_validated(activation['id'])
    
    # 7. Log successful validation
    log_validation(payload.license_key, payload.hardware_fingerprint, 'valid')
    
    # Calculate days until expiry
    days_until_expiry = (license['expires_at'] - datetime.now()).days
    
    return {
        "valid": True,
        "is_blocked": False,
        "expires_at": license['expires_at'],
        "days_remaining": days_until_expiry,
        "customer_name": license['customer_name'],
        "company_name": license['company_name']
    }

@app.get("/info/{license_key}")
async def get_license_info(license_key: str):
    """Get public license info (for display purposes)."""
    license = get_license(license_key)
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    
    return {
        "customer_name": license['customer_name'],
        "company_name": license['company_name'],
        "expires_at": license['expires_at'],
        "is_blocked": license['is_blocked']
    }

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "layer": "1", "service": "license-server"}

# Serve admin panel (if built)
# Path handling for different execution contexts
# When run from backend/ dir: ../frontend/dist
# When run from root: frontend/dist
import os
frontend_dist_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(frontend_dist_path):
    @app.get("/")
    async def serve_admin():
        return FileResponse(os.path.join(frontend_dist_path, "index.html"))
    
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="admin")
    print(f"✅ Serving admin panel from: {frontend_dist_path}")
else:
    print(f"⚠️ Admin panel not found at: {frontend_dist_path}")
    print("   Frontend not available. Use API endpoints directly.")

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
