"""
Users API endpoints.
Provides user listing and lookup (persona data for the demo).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserListResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse)
async def list_users(db: Session = Depends(get_db)):
    """List all users (personas) in the system."""
    users = db.query(User).all()
    user_responses = []
    for user in users:
        user_responses.append(
            UserResponse(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
                registration_date=user.registration_date,
                risk_segment=user.risk_segment,
                transaction_count=len(user.transactions),
            )
        )
    return UserListResponse(users=user_responses, total=len(user_responses))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get a specific user by ID."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        registration_date=user.registration_date,
        risk_segment=user.risk_segment,
        transaction_count=len(user.transactions),
    )
