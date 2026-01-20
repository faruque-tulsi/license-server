# Layer 1 - License Server Setup Guide

## Overview

Layer 1 is your local license server that manages license generation, activation, and validation.

## Architecture

```
┌─────────────────────────────────────┐
│   Weighbridge Application           │
│   (checks license on startup)       │
└──────────────┬──────────────────────┘
               │
          validates ↓
┌─────────────────────────────────────┐
│   Layer 1 - Local License Server    │
│   - Admin Panel (manage licenses)   │
│   - Activation API                  │
│   - Validation API                  │
└──────────────┬──────────────────────┘

```

## Setup Steps

### 1. Database Setup

**Option A: MySQL (Local)**
```bash
# Install MySQL
# Create database
mysql -u root -p
```

```sql
CREATE DATABASE license_server_db;
```

**Import schema**:
```bash
mysql -u root -p license_server_db < database.sql
```

Default admin credentials: `admin` / `admin123`

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
# DB_HOST=localhost
# DB_USER=root
# DB_PASSWORD=your_password
# DB_NAME=license_server_db


# Run server
python main.py
```

Backend will run on `http://localhost:8000`

### 3. Admin Panel Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Admin panel will run on `http://localhost:3000`

**Login**: `admin` / `admin123`

### 4. Production Build

**Frontend**:
```bash
cd frontend
npm run build
```

Built files will be in `frontend/dist/` and automatically served by backend.

**Deploy backend**:
```bash
# Run on network
python backend/main.py
```

Access from devices on network: `http://YOUR_IP:8000`

---

## Usage

### Generate License

1. Login to admin panel
2. Go to "Generate License"
3. Fill in customer details
4. Set expiry date and max activations
5. Click "Generate"
6. Copy license key and share with customer

### Activate License (Client Side)

```python
from license_system.client.license_manager import LicenseManager

manager = LicenseManager(server_url="http://YOUR_SERVER:8000")
result = manager.activate("WB-XXXXXXXX-XXXXXXXX")

if result['success']:
    print("Activated!")
else:
    print(result['message'])
```

### Validate License

```python
if manager.is_valid():
    print("License is valid")
    info = manager.get_license_info()
    print(f"Expires in {info['days_remaining']} days")
else:
    print("License invalid")
```

### Manage Licenses

- **View all licenses**: Admin panel → "All Licenses"
- **Block license**: Click "Block" button
- **Unblock license**: Click "Unblock" button
- **View activations**: Admin panel → "Activations"
- **Deactivate device**: Click "Deactivate" button

---

## API Endpoints

### Admin Endpoints (require Bearer token)

- `POST /admin/login` - Admin login
- `POST /admin/generate` - Generate license
- `GET /admin/licenses` - List all licenses
- `GET /admin/licenses/{key}` - Get license details
- `POST /admin/block` - Block license
- `POST /admin/unblock` - Unblock license
- `POST /admin/extend` - Extend expiry
- `GET /admin/activations` - List activations
- `DELETE /admin/activation/{id}` - Deactivate device
- `GET /admin/stats` - Get statistics

### Client Endpoints (no auth required)

- `POST /activate` - Activate license
- `POST /validate` - Validate license
- `GET /info/{license_key}` - Get license info

---

## Integration with Weighbridge App

See `INTEGRATION_GUIDE.md` for detailed integration steps.

**Quick example**:

```python
# In your main application file
from license_system.client.license_manager import LicenseManager

license_mgr = LicenseManager(server_url="http://localhost:8000")

# Check on startup
if not license_mgr.is_valid():
    # Show activation dialog
    from license_system.client.ui_components import show_activation_dialog
    license_key = show_activation_dialog()
    
    if license_key:
        result = license_mgr.activate(license_key)
        if not result['success']:
            print(result['message'])
            exit(1)
    else:
        exit(1)

# Periodic check (daily)
import threading
def daily_check():
    while True:
        time.sleep(86400)  # 24 hours
        if not license_mgr.is_valid():
            # Show warning/block screen
            pass

threading.Thread(target=daily_check, daemon=True).start()
```

---



---

## Troubleshooting

### Database Connection Error
- Check MySQL is running
- Verify credentials in environment variables
- Ensure database `license_server_db` exists



### License Validation Fails Offline
- Offline grace period: 7 days
- After 7 days, requires online validation

---

## Security Notes

- Admin panel requires login
- License keys are unique and hardware-bound
- All validations logged to `validation_logs`
- Remote system provides master override capability
- Use HTTPS in production

---

## Next Steps

1. ✅ Set up database
2. ✅ Run backend
3. ✅ Access admin panel
4. ✅ Generate test license
5. ✅ Test activation
6. ➡️ Integrate with weighbridge app

---

## Support

For issues or questions, refer to:
- `implementation_plan.md` - Full technical details
- `INTEGRATION_GUIDE.md` - Weighbridge integration steps

