from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ── Request Schemas ──────────────────────────────────────────

class HospitalCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    address: str = Field(..., min_length=5)
    phone: str = Field(..., min_length=5)
    email: EmailStr
    admin_name: str = Field(..., min_length=2, description="Name of the hospital admin user")
    admin_email: EmailStr = Field(..., description="Login email for hospital admin")
    admin_password: str = Field(..., min_length=6, description="Password for hospital admin")


class HospitalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    address: Optional[str] = Field(None, min_length=5)
    phone: Optional[str] = Field(None, min_length=5)
    email: Optional[EmailStr] = None


class HospitalStatusUpdate(BaseModel):
    is_active: bool


# ── Response Schemas ─────────────────────────────────────────

class HospitalResponse(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    email: str
    is_active: bool
    admin_user_id: Optional[str] = None
    admin_name: Optional[str] = None
    admin_email: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class HospitalListResponse(BaseModel):
    hospitals: list[HospitalResponse]
    total: int


# ── Hospital Admin Management ────────────────────────────────

class HospitalAdminUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=5, max_length=40)


class HospitalAdminPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6, description="New login password")


class HospitalAdminReplace(BaseModel):
    admin_name: str = Field(..., min_length=2, max_length=200)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=6)
    admin_phone: Optional[str] = Field(None, min_length=5, max_length=40)


class HospitalAdminResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    hospital_id: Optional[str] = None
    hospital_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class HospitalAdminListResponse(BaseModel):
    admins: list[HospitalAdminResponse]
    total: int


class PlatformStatsResponse(BaseModel):
    total_hospitals: int
    active_hospitals: int
    total_doctors: int
    total_patients: int
    total_guardians: int
    total_users: int
