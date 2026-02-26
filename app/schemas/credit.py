"""
Pydantic schemas for the Credit Assessment API.
Covers request/response models, EMI offers, and score breakdowns.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """Individual factor contributions to the credit score."""
    purchase_frequency: float = Field(..., ge=0, le=100, description="Purchase frequency score (0-100)")
    deal_redemption: float = Field(..., ge=0, le=100, description="Deal/coupon usage quality score (0-100)")
    category_diversification: float = Field(..., ge=0, le=100, description="Category diversity index (0-100)")
    gmv_growth: float = Field(..., ge=0, le=100, description="GMV growth trajectory score (0-100)")
    return_behavior: float = Field(..., ge=0, le=100, description="Return behavior score (higher = fewer returns)")
    fraud_velocity: float = Field(..., ge=0, le=100, description="Fraud velocity score (0 = flagged)")


class EMIOffer(BaseModel):
    """EMI tenure option with calculated monthly payment."""
    tenure_months: int = Field(..., description="EMI tenure in months")
    monthly_amount: float = Field(..., description="Monthly EMI amount")
    interest_rate: float = Field(..., description="Annual interest rate (%)")
    total_amount: float = Field(..., description="Total payable amount")
    processing_fee: float = Field(0.0, description="One-time processing fee")


class CreditAssessmentRequest(BaseModel):
    """Request payload for credit assessment at checkout."""
    user_id: str = Field(..., description="User to assess")
    requested_amount: float = Field(..., gt=0, description="Purchase amount for BNPL")


class CreditAssessmentResponse(BaseModel):
    """Complete credit assessment result."""
    user_id: str = Field(..., description="Assessed user ID")
    user_name: str = Field("", description="User display name")
    risk_segment: str = Field("", description="User persona tag")

    # Decision
    approved: bool = Field(..., description="Whether BNPL is approved")
    credit_score: float = Field(..., ge=0, le=100, description="Final credit score (0-100)")
    credit_limit: float = Field(0.0, description="Recommended credit limit (₹)")

    # Breakdown
    score_breakdown: ScoreBreakdown = Field(..., description="Individual factor scores")

    # EMI Offers (only if approved)
    emi_offers: list[EMIOffer] = Field(default_factory=list, description="Available EMI options")

    # Narrative
    narrative: str = Field("", description="AI-generated credit decision explanation")

    # Flags
    fraud_flagged: bool = Field(False, description="Whether fraud velocity was triggered")

    # Metadata
    requested_amount: float = Field(0.0, description="Original requested amount")
    assessment_timestamp: Optional[str] = Field(None, description="ISO timestamp of assessment")
