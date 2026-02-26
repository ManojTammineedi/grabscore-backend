"""
Transaction model representing GrabOn purchase transactions.
Follows the MCP Transaction Data Schema from the Architecture doc.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing transaction ID"
    )
    transaction_id: Mapped[str] = mapped_column(
        String(36),
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
        doc="Unique transaction identifier (UUID)"
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.user_id"),
        nullable=False,
        index=True,
        doc="Reference to the user who made this transaction"
    )
    merchant_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Merchant identifier"
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Product/service category"
    )
    gmv_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Gross merchandise value of the transaction"
    )
    coupon_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether a coupon/deal was used"
    )
    payment_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UPI",
        doc="Payment mode: UPI, Card, Wallet, COD"
    )
    return_flag: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the item was returned"
    )
    transaction_timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        index=True,
        doc="When the transaction occurred"
    )

    # Relationship to user
    user = relationship("User", back_populates="transactions")

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.transaction_id}, user={self.user_id}, "
            f"amount={self.gmv_amount}, category={self.category})>"
        )
