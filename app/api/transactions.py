"""
Transactions API endpoints.
MCP-compliant transaction data access with filtering.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionResponse, TransactionListResponse

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/{user_id}", response_model=TransactionListResponse)
async def get_user_transactions(
    user_id: str,
    start_date: Optional[datetime] = Query(None, description="Filter: start of time range"),
    end_date: Optional[datetime] = Query(None, description="Filter: end of time range"),
    merchant: Optional[str] = Query(None, description="Filter: merchant ID"),
    category: Optional[str] = Query(None, description="Filter: product category"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Get transaction history for a user with optional filters.
    MCP-compliant endpoint supporting time range, merchant, and category filters.
    """
    # Verify user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Build query with filters
    query = db.query(Transaction).filter(Transaction.user_id == user_id)

    if start_date:
        query = query.filter(Transaction.transaction_timestamp >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_timestamp <= end_date)
    if merchant:
        query = query.filter(Transaction.merchant_id == merchant)
    if category:
        query = query.filter(Transaction.category == category)

    # Get total count before pagination
    total = query.count()

    # Apply pagination and ordering
    transactions = (
        query
        .order_by(Transaction.transaction_timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return TransactionListResponse(
        transactions=[
            TransactionResponse(
                transaction_id=t.transaction_id,
                user_id=t.user_id,
                merchant_id=t.merchant_id,
                category=t.category,
                gmv_amount=t.gmv_amount,
                coupon_used=t.coupon_used,
                payment_mode=t.payment_mode,
                return_flag=t.return_flag,
                transaction_timestamp=t.transaction_timestamp,
            )
            for t in transactions
        ],
        total=total,
        user_id=user_id,
    )
