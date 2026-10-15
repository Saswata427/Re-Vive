from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────

class CreatableRole(str, Enum):
    """Roles that a hospital admin can create."""
    DOCTOR = "doctor"
    PATIENT = "patient"
    GUARDIAN = "guardian"


# ── Request Schemas ──────────────────────────────────────────

class UserCreate(BaseModel):
    role: CreatableRole
    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = Field(None, min_length=5)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class UserStatusUpdate(BaseModel):
    is_active: bool


class PatientProfileUpsert(BaseModel):
    """Behavioural recovery profile fields a hospital admin may set."""
    primary_condition: Optional[str] = Field(None, max_length=300)
    program_start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    sobriety_date: Optional[str] = Field(None, description="YYYY-MM-DD, drives abstinence count")
    therapy_program: Optional[str] = Field(None, max_length=300)
    emergency_contact: Optional[str] = Field(None, max_length=200)
    medical_notes: Optional[str] = Field(None, max_length=5000)


class PatientProfileResponse(BaseModel):
    primary_condition: Optional[str] = None
    program_start_date: Optional[str] = None
    sobriety_date: Optional[str] = None
    therapy_program: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_notes: Optional[str] = None
    abstinence_days: Optional[int] = None


class AssignmentCreate(BaseModel):
    doctor_id: str = Field(..., description="ID of the doctor")
    patient_id: str = Field(..., description="ID of the patient")


class GuardianLinkRequest(BaseModel):
    guardian_id: str = Field(..., description="ID of the guardian")
    patient_id: str = Field(..., description="ID of the patient")


# ── Response Schemas ─────────────────────────────────────────

class HospitalUserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    hospital_id: Optional[str] = None
    assigned_patients: list[str] = []
    linked_patient_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserListResponse(BaseModel):
    users: list[HospitalUserResponse]
    total: int


class HospitalDashboardStats(BaseModel):
    total_doctors: int
    total_patients: int
    total_guardians: int
    total_users: int
    active_users: int


class AssignmentResponse(BaseModel):
    id: str
    doctor_id: str
    doctor_name: str
    doctor_email: str
    patient_id: str
    patient_name: str
    patient_email: str
    created_at: Optional[str] = None


class AssignmentListResponse(BaseModel):
    assignments: list[AssignmentResponse]
    total: int


class GuardianLinkResponse(BaseModel):
    guardian_id: str
    guardian_name: str
    patient_id: str
    patient_name: str


class MessageResponse(BaseModel):
    message: str
