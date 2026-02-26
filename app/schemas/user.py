"""Pydantic schemas for User API responses."""

from datetime import datetime
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User data returned by the API."""
    user_id: str = Field(..., description="Unique user identifier")
    name: str = Field(..., description="User display name")
    email: str = Field(..., description="User email address")
    registration_date: datetime = Field(..., description="Account registration date")
    risk_segment: str = Field(..., description="Persona classification tag")
    transaction_count: int = Field(0, description="Total number of transactions")

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated list of users."""
    users: list[UserResponse]
    total: int
