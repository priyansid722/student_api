"""Pydantic schemas for data validation and API response serialization.

These models define and enforce the exact data structure expected from clients
and returned by the FastAPI endpoints.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, model_validator


class StudentCreate(BaseModel):
    """Schema for creating a new student record.

    Validates that:
    1. 'name' is non-empty.
    2. 'date_of_birth' is a valid date (YYYY-MM-DD).
    3. Either an 'email' (must be a valid email format) or a 'phone' (or both) is provided.
    """
    name: str = Field(min_length=1, description="Student's full name")
    date_of_birth: date = Field(description="Date of birth in YYYY-MM-DD format")
    email: Optional[EmailStr] = Field(default=None, description="Unique email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    course: Optional[str] = Field(default=None, description="Enrolled program or course")
    address: Optional[str] = Field(default=None, description="City or address of residence")
    enrollment_date: Optional[date] = Field(default=None, description="Date of enrollment (YYYY-MM-DD)")

    @model_validator(mode="after")
    def need_contact(self):
        """Ensure at least one contact method (email or phone) is provided."""
        if not self.email and not self.phone:
            raise ValueError("Provide at least an email or a phone number")
        return self


class StudentUpdate(BaseModel):
    """Schema for updating an existing student (PATCH).

    All fields are optional because the client only sends fields they wish to update.
    """
    name: Optional[str] = Field(default=None, min_length=1, description="Student's full name")
    date_of_birth: Optional[date] = Field(default=None, description="Date of birth (YYYY-MM-DD)")
    email: Optional[EmailStr] = Field(default=None, description="Updated unique email address")
    phone: Optional[str] = Field(default=None, description="Updated phone number")
    course: Optional[str] = Field(default=None, description="Updated course")
    address: Optional[str] = Field(default=None, description="Updated address")
    enrollment_date: Optional[date] = Field(default=None, description="Updated enrollment date (YYYY-MM-DD)")


class StudentOut(BaseModel):
    """Schema for serialized student output sent back to the API client."""
    id: int
    name: str
    date_of_birth: str
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[str] = None


class AskRequest(BaseModel):
    """Schema for the question sent to the LLM assistant.

    The question length is restricted between 3 and 300 characters to prevent prompt injection
    and ensure prompt token efficiency.
    """
    question: str = Field(min_length=3, max_length=300, description="Natural language question about students")


class AskResponse(BaseModel):
    """Schema for the LLM assistant's answer."""
    answer: str
