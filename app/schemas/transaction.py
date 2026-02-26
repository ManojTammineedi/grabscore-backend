"""Pydantic schemas for Transaction API responses and filters."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TransactionResponse(BaseModel):
    """Single transaction record returned by the API."""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    user_id: str = Field(..., description="User who made the transaction")
    merchant_id: str = Field(..., description="Merchant identifier")
    category: str = Field(..., description="Product/service category")
    gmv_amount: float = Field(..., description="Gross merchandise value")
    coupon_used: bool = Field(..., description="Whether a coupon was used")
    payment_mode: str = Field(..., description="Payment mode (UPI/Card/Wallet/COD)")
    return_flag: bool = Field(..., description="Whether the item was returned")
    transaction_timestamp: datetime = Field(..., description="Transaction timestamp")

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    """List of transaction records with metadata."""
    transactions: list[TransactionResponse]
    total: int
    user_id: str


class TransactionFilter(BaseModel):
    """Query filters for transaction data (MCP compliance)."""
    start_date: Optional[datetime] = Field(None, description="Filter: start of time range")
    end_date: Optional[datetime] = Field(None, description="Filter: end of time range")
    merchant: Optional[str] = Field(None, description="Filter: merchant ID")
    category: Optional[str] = Field(None, description="Filter: product category")
