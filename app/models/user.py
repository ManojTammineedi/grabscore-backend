"""
User model representing GrabOn platform users.
Each user has a persona tag (risk_segment) for demo purposes.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique user identifier (UUID)"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="User display name"
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="User email address"
    )
    registration_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        doc="Account registration timestamp"
    )
    risk_segment: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
        doc="Persona tag: new_user, casual_shopper, deal_hunter, regular_user, power_user"
    )

    # Relationship to transactions
    transactions = relationship("Transaction", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, name={self.name}, segment={self.risk_segment})>"
