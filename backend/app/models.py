# Pydantic models for FlatWatch API
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class TransactionBase(BaseModel):
    amount: float = Field(gt=0, description="Transaction amount must be positive")
    transaction_type: str = Field(pattern="^(inflow|outflow)$")
    description: Optional[str] = None
    vpa: Optional[str] = None


class TransactionCreate(TransactionBase):
    receipt_path: Optional[str] = None


class Transaction(TransactionBase):
    id: int
    timestamp: datetime
    receipt_path: Optional[str] = None
    verified: bool = False
    created_at: datetime
    entered_by: Optional[int] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None

    # Attribution info (joined data)
    entered_by_name: Optional[str] = None
    entered_by_role: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_by_role: Optional[str] = None

    model_config = {"from_attributes": True}


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    flat_number: Optional[str] = None


class UserCreate(UserBase):
    firebase_uid: str


class User(UserBase):
    id: int
    firebase_uid: str
    role: str = "resident"
    created_at: datetime

    model_config = {"from_attributes": True}


class ChallengeBase(BaseModel):
    transaction_id: int
    reason: str


class ChallengeCreate(ChallengeBase):
    user_id: int


class Challenge(ChallengeBase):
    id: int
    user_id: int
    status: str = "pending"
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
