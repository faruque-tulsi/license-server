# Layer 1 License Server - Pydantic Models
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime

class LicenseCreate(BaseModel):
    customer_name: str
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    expires_at: datetime
    max_activations: int = 1
    restricted_fingerprint: str
    notes: Optional[str] = None

    @field_validator('company_name', 'email', 'phone', 'notes', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

class LicenseResponse(BaseModel):
    id: int
    license_key: str
    customer_name: str
    company_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    generated_at: datetime
    updated_at: Optional[datetime] = None  # Added field
    expires_at: datetime
    max_activations: int
    is_blocked: bool
    block_message: Optional[str]
    notes: Optional[str]

class ActivateRequest(BaseModel):
    license_key: str
    hardware_fingerprint: str
    device_name: Optional[str] = None

class ValidateRequest(BaseModel):
    license_key: str
    hardware_fingerprint: str

class BlockRequest(BaseModel):
    license_key: str
    message: Optional[str] = "License has been blocked by administrator"

class ExtendRequest(BaseModel):
    license_key: str
    new_expiry: datetime

class AdminLogin(BaseModel):
    username: str
    password: str
