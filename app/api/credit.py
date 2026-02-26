"""
Credit Assessment API endpoints.
Core BNPL eligibility engine — orchestrates scoring, EMI, narrative, and caching.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import cache_get, cache_set
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.credit import (
    CreditAssessmentRequest,
    CreditAssessmentResponse,
)

# True Architecture Services
from app.services.fraud_detection import FraudDetectionService
from app.services.claude_service import ClaudeService
from app.services.gemini_service import GeminiService
from app.services.payu_client import PayuLazyPayClient

# MCP Server local imports
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from mcp_server import get_user_transactions, check_fraud_velocity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/credit", tags=["Credit Assessment"])


@router.post("/assess", response_model=CreditAssessmentResponse)
async def assess_credit(
    request: CreditAssessmentRequest,
    db: Session = Depends(get_db),
):
    """
    Main credit assessment endpoint.
    Orchestrates: fraud check -> Gemini scoring & narrative -> PayU EMI generation.
    """
    cache_key = f"credit:score:{request.user_id}:{request.requested_amount}"
    cached = cache_get(cache_key)
    if cached:
        logger.info("[CACHE HIT] Returning cached assessment for %s", request.user_id)
        return CreditAssessmentResponse(**cached)

    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")

    # 1. Fetch transactions via MCP
    transactions_dict = get_user_transactions(request.user_id)
    transactions_json = json.dumps(transactions_dict, indent=2)

    # Compute data points for Claude backward-compatibility
    transactions = db.query(Transaction).filter(Transaction.user_id == request.user_id).all()
    account_age_days = (datetime.now() - user.registration_date).days

    # 2. Fraud velocity check via MCP
    logger.info("[MCP FRAUD CHECK] %s | account age: %d days", user.name, account_age_days)
    fraud_result = check_fraud_velocity(request.user_id)
    fraud_flagged = fraud_result.get("fraud_velocity_flagged", False)
    logger.info("[MCP FRAUD CHECK] flagged=%s", fraud_flagged)

    # 3. Gemini AI scoring & narrative
    logger.info("[GEMINI API] Calling Gemini LLM for %s...", user.name)
    llm_result = GeminiService.generate_narrative_and_score(
        user_name=user.name,
        transactions_json=transactions_json,
        fraud_flagged=fraud_flagged,
        account_age_days=account_age_days,
    )
    
    logger.info("[GEMINI API] Score: %s | Approved: %s | Limit: %s",
                llm_result.get("credit_score", 0),
                llm_result.get("approved"),
                llm_result.get("credit_limit", 0))

    approved = llm_result.get("approved", False)
    score = llm_result.get("credit_score", 0.0)
    credit_limit = llm_result.get("credit_limit", 0.0)
    score_breakdown = llm_result.get("score_breakdown", {})
    narrative = llm_result.get("narrative", "Assessment incomplete.")

    if request.requested_amount > credit_limit:
        approved = False

    # 3. PayU EMI offers
    emi_offers = []
    if approved:
        logger.info("[PAYU API] Fetching EMI offers for %.0f...", request.requested_amount)
        emi_offers = await PayuLazyPayClient.fetch_emi_offers(request.requested_amount, credit_limit)
        logger.info("[PAYU API] %d offers received", len(emi_offers))

    response = CreditAssessmentResponse(
        user_id=user.user_id,
        user_name=user.name,
        risk_segment=user.risk_segment,
        approved=approved,
        credit_score=score,
        credit_limit=credit_limit,
        score_breakdown=score_breakdown,
        emi_offers=emi_offers,
        narrative=narrative,
        fraud_flagged=fraud_flagged,
        requested_amount=request.requested_amount,
        assessment_timestamp=datetime.now().isoformat(),
    )

    cache_set(cache_key, response.model_dump(), ttl=300)
    return response


# ─── PayU Payment Page Redirect ─────────────────────────────────

class PaymentFormRequest(BaseModel):
    user_id: str
    amount: float
    tenure_months: int


class PaymentFormResponse(BaseModel):
    payment_url: str
    form_params: dict


@router.post("/payu/initiate", response_model=PaymentFormResponse)
async def initiate_payu_payment(
    request: PaymentFormRequest,
    db: Session = Depends(get_db),
):
    """
    Generates PayU form parameters + SHA-512 hash.
    The frontend receives these and submits a hidden HTML form that
    redirects the browser to the actual PayU Sandbox checkout page.
    """
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")

    logger.info("[PAYU REDIRECT] Generating payment form for %s | amount=%.0f | %dM EMI",
                user.name, request.amount, request.tenure_months)

    # Get EMI details to pass back to frontend for confirmation page
    # In a real app, this should be saved to DB as "pending transaction" 
    # and retrieved upon success, but for this prototype we pass via URL params
    # We'll use the EMICalculator to get the exact breakdown we showed the user
    from app.services.emi_calculator import EMICalculator
    
    offers = EMICalculator.generate_offers(request.amount, request.amount + 1) # Force approval logic for calc
    selected_offer = next((o for o in offers if o.tenure_months == request.tenure_months), None)
    
    monthly_param = selected_offer.monthly_amount if selected_offer else 0
    total_param = selected_offer.total_amount if selected_offer else request.amount
    rate_param = selected_offer.interest_rate if selected_offer else 0
    fee_param = selected_offer.processing_fee if selected_offer else 0

    # surl/furl: where PayU redirects after success/failure
    base_url = "http://localhost:3000"
    surl = f"{base_url}/confirmation?user_id={request.user_id}&amount={request.amount}&tenure={request.tenure_months}&status=success&monthly={monthly_param}&total={total_param}&rate={rate_param}&fee={fee_param}"
    furl = f"{base_url}/confirmation?user_id={request.user_id}&amount={request.amount}&tenure={request.tenure_months}&status=failed"

    form_data = PayuLazyPayClient.generate_payment_form(
        amount=request.amount,
        user_name=user.name,
        user_email=user.email,
        tenure_months=request.tenure_months,
        surl=surl,
        furl=furl,
    )

    return PaymentFormResponse(**form_data)


# ─── Quick Score Lookup ──────────────────────────────────────────

@router.get("/score/{user_id}")
async def get_cached_score(user_id: str, db: Session = Depends(get_db)):
    """Quick score lookup from cache or local fallback."""
    cached = cache_get(f"credit:score:{user_id}:*")
    if cached:
        return {
            "user_id": user_id,
            "credit_score": cached.get("credit_score"),
            "approved": cached.get("approved"),
            "breakdown": cached.get("score_breakdown"),
        }

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    total_gmv = sum(t.gmv_amount for t in transactions) if transactions else 0
    coupon_count = sum(1 for t in transactions if t.coupon_used) if transactions else 0
    return_count = sum(1 for t in transactions if t.return_flag) if transactions else 0
    coupon_rate = coupon_count / len(transactions) if transactions else 0
    return_rate = return_count / len(transactions) if transactions else 0
    categories_count = len(set(t.category for t in transactions)) if transactions else 0
    account_age_days = (datetime.now() - user.registration_date).days
    fraud_result = FraudDetectionService.check_velocity(user)

    claude_result = ClaudeService._generate_mock_fallback(
        name=user.name, tx=len(transactions), gmv=total_gmv,
        c_rate=coupon_rate, r_rate=return_rate, cat=categories_count,
        age=account_age_days, fraud=fraud_result["flagged"],
    )

    return {
        "user_id": user_id,
        "credit_score": claude_result.get("credit_score"),
        "approved": claude_result.get("approved"),
        "breakdown": claude_result.get("score_breakdown"),
    }
