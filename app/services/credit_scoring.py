"""
Credit Scoring Engine - Core business logic.

Computes a credit score from 6 behavioral signals derived from
transaction history. Each factor produces a 0-100 sub-score, which
are combined via weighted average to produce the final score.

Weights:
  - Purchase Frequency:       20%
  - Deal Redemption:          15%
  - Category Diversification: 15%
  - GMV Growth:               25%
  - Return Behavior:          15%
  - Fraud Velocity:           10%
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.credit import ScoreBreakdown
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Score weights (must sum to 1.0)
WEIGHTS = {
    "purchase_frequency": 0.20,
    "deal_redemption": 0.15,
    "category_diversification": 0.15,
    "gmv_growth": 0.25,
    "return_behavior": 0.15,
    "fraud_velocity": 0.10,
}


class CreditScoringEngine:
    """
    Stateless credit scoring engine.
    Accepts a DB session and user_id, fetches transaction data,
    computes sub-scores, and returns the final assessment.
    """

    def __init__(self, db: Session):
        self.db = db

    def compute_score(self, user: User, transactions: list[Transaction]) -> tuple[float, ScoreBreakdown]:
        """
        Compute credit score and breakdown for a user.
        Returns: (final_score, score_breakdown)
        """
        breakdown = ScoreBreakdown(
            purchase_frequency=self._purchase_frequency_score(transactions),
            deal_redemption=self._deal_redemption_score(transactions),
            category_diversification=self._category_diversification_score(transactions),
            gmv_growth=self._gmv_growth_score(transactions),
            return_behavior=self._return_behavior_score(transactions),
            fraud_velocity=self._fraud_velocity_score(user),
        )

        # Weighted average
        final_score = (
            breakdown.purchase_frequency * WEIGHTS["purchase_frequency"]
            + breakdown.deal_redemption * WEIGHTS["deal_redemption"]
            + breakdown.category_diversification * WEIGHTS["category_diversification"]
            + breakdown.gmv_growth * WEIGHTS["gmv_growth"]
            + breakdown.return_behavior * WEIGHTS["return_behavior"]
            + breakdown.fraud_velocity * WEIGHTS["fraud_velocity"]
        )

        # If fraud flagged, cap score harshly
        if breakdown.fraud_velocity == 0:
            final_score = min(final_score, 10.0)

        return round(final_score, 2), breakdown

    def compute_credit_limit(self, score: float, requested_amount: float) -> float:
        """
        Determine credit limit based on score.
        Higher scores get up to MAX_CREDIT_LIMIT.
        """
        if score < settings.APPROVAL_THRESHOLD:
            return 0.0

        # Linear scaling from MIN to MAX based on score above threshold
        score_ratio = (score - settings.APPROVAL_THRESHOLD) / (100 - settings.APPROVAL_THRESHOLD)
        limit = settings.MIN_CREDIT_LIMIT + score_ratio * (settings.MAX_CREDIT_LIMIT - settings.MIN_CREDIT_LIMIT)

        # Ensure limit covers requested amount if approved
        return round(max(limit, min(requested_amount * 1.2, settings.MAX_CREDIT_LIMIT)), 2)

    def is_approved(self, score: float) -> bool:
        """Check if score meets approval threshold."""
        return score >= settings.APPROVAL_THRESHOLD

    # ─── Individual Scoring Factors ─────────────────────────────────

    def _purchase_frequency_score(self, transactions: list[Transaction]) -> float:
        """
        Score based on purchase frequency over the last 12 months.
        Benchmarks: 0 txns = 0, 10 = 30, 50 = 60, 100+ = 90, 200+ = 100.
        """
        if not transactions:
            return 0.0

        twelve_months_ago = datetime.now() - timedelta(days=365)
        recent = [t for t in transactions if t.transaction_timestamp >= twelve_months_ago]
        count = len(recent)

        if count == 0:
            return 0.0
        elif count < 10:
            return min(count * 3.0, 30.0)
        elif count < 50:
            return 30.0 + (count - 10) * 0.75
        elif count < 100:
            return 60.0 + (count - 50) * 0.6
        elif count < 200:
            return 90.0 + (count - 100) * 0.1
        else:
            return 100.0

    def _deal_redemption_score(self, transactions: list[Transaction]) -> float:
        """
        Score based on coupon/deal usage rate — a quality signal.
        Higher coupon usage indicates engagement with the platform.
        50-85% coupon rate is the sweet spot.
        """
        if not transactions:
            return 0.0

        coupon_count = sum(1 for t in transactions if t.coupon_used)
        rate = coupon_count / len(transactions)

        if rate < 0.1:
            return 20.0
        elif rate < 0.3:
            return 40.0
        elif rate < 0.5:
            return 60.0
        elif rate <= 0.85:
            return 85.0 + (rate - 0.5) * 42.86  # Scale to 85-100
        else:
            # Very high rate (>85%) might indicate deal-only behavior
            return 75.0

    def _category_diversification_score(self, transactions: list[Transaction]) -> float:
        """
        Score based on diversity of purchase categories.
        More categories = more reliable consumer behavior.
        """
        if not transactions:
            return 0.0

        categories = set(t.category for t in transactions)
        unique_count = len(categories)

        if unique_count == 1:
            return 20.0
        elif unique_count <= 3:
            return 40.0
        elif unique_count <= 5:
            return 60.0
        elif unique_count <= 8:
            return 80.0
        else:
            return 100.0

    def _gmv_growth_score(self, transactions: list[Transaction]) -> float:
        """
        Score based on GMV growth trajectory over 12 months.
        Compares first-half vs second-half total GMV.
        Positive growth is rewarded; stagnation scores moderately.
        """
        if not transactions:
            return 0.0

        twelve_months_ago = datetime.now() - timedelta(days=365)
        six_months_ago = datetime.now() - timedelta(days=180)

        first_half = [t for t in transactions
                      if twelve_months_ago <= t.transaction_timestamp < six_months_ago]
        second_half = [t for t in transactions
                       if t.transaction_timestamp >= six_months_ago]

        gmv_first = sum(t.gmv_amount for t in first_half)
        gmv_second = sum(t.gmv_amount for t in second_half)

        # Total GMV baseline score
        total_gmv = gmv_first + gmv_second
        if total_gmv < 1000:
            base = 15.0
        elif total_gmv < 5000:
            base = 30.0
        elif total_gmv < 20000:
            base = 50.0
        elif total_gmv < 50000:
            base = 70.0
        else:
            base = 85.0

        # Growth trajectory bonus
        if gmv_first > 0:
            growth_rate = (gmv_second - gmv_first) / gmv_first
            if growth_rate > 0.3:
                base = min(base + 15, 100)
            elif growth_rate > 0:
                base = min(base + 8, 100)
            elif growth_rate < -0.3:
                base = max(base - 10, 0)

        return round(min(base, 100), 2)

    def _return_behavior_score(self, transactions: list[Transaction]) -> float:
        """
        Score based on return rate — lower returns = higher score.
        0% returns = 100, >15% returns = 20.
        """
        if not transactions:
            return 50.0  # Neutral for no data

        return_count = sum(1 for t in transactions if t.return_flag)
        return_rate = return_count / len(transactions)

        if return_rate == 0:
            return 100.0
        elif return_rate < 0.02:
            return 90.0
        elif return_rate < 0.05:
            return 75.0
        elif return_rate < 0.10:
            return 55.0
        elif return_rate < 0.15:
            return 35.0
        else:
            return 20.0

    def _fraud_velocity_score(self, user: User) -> float:
        """
        Fraud velocity check: if user registered < FRAUD_VELOCITY_DAYS ago, score = 0.
        This triggers an auto-reject via the final score cap.
        """
        days_since_registration = (datetime.now() - user.registration_date).days

        if days_since_registration < settings.FRAUD_VELOCITY_DAYS:
            logger.warning(f"Fraud velocity flag: user {user.user_id} registered {days_since_registration} days ago")
            return 0.0

        if days_since_registration < 30:
            return 40.0
        elif days_since_registration < 90:
            return 65.0
        elif days_since_registration < 365:
            return 85.0
        else:
            return 100.0
