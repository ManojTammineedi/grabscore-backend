"""
Credit Narrative Generator.

Produces human-readable, data-backed explanations for credit decisions.
Uses template-based generation for the prototype, with a hook for
Claude AI integration.
"""

import logging
from app.schemas.credit import ScoreBreakdown

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """
    Generates explainable credit narratives from score breakdown data.
    All narratives reference actual behavioral metrics — no opaque scoring.
    """

    @staticmethod
    def generate(
        user_name: str,
        approved: bool,
        score: float,
        breakdown: ScoreBreakdown,
        credit_limit: float,
        fraud_flagged: bool,
        transaction_count: int,
        total_gmv: float,
        coupon_rate: float,
        return_rate: float,
        categories_count: int,
        account_age_days: int,
    ) -> str:
        """
        Generate a data-backed narrative explanation.

        Args:
            user_name: Display name of the user
            approved: Whether the user was approved
            score: Final credit score
            breakdown: Individual factor scores
            credit_limit: Assigned credit limit
            fraud_flagged: Whether fraud velocity was triggered
            transaction_count: Total number of transactions
            total_gmv: Sum of all GMV
            coupon_rate: Percentage of transactions with coupons
            return_rate: Percentage of transactions returned
            categories_count: Number of unique purchase categories
            account_age_days: Days since registration
        """
        if fraud_flagged:
            return _fraud_narrative(user_name, account_age_days)

        if not approved:
            return _rejection_narrative(
                user_name, score, transaction_count, total_gmv,
                coupon_rate, return_rate, account_age_days
            )

        return _approval_narrative(
            user_name, score, credit_limit, breakdown,
            transaction_count, total_gmv, coupon_rate,
            return_rate, categories_count, account_age_days
        )


def _fraud_narrative(name: str, age_days: int) -> str:
    return (
        f"Hi {name}, your BNPL application could not be approved at this time. "
        f"Your account was created just {age_days} day(s) ago, and our security policies "
        f"require a minimum account history of 7 days before BNPL eligibility. "
        f"This policy helps protect both you and our merchants from fraudulent activity. "
        f"Please try again after your account has matured."
    )


def _rejection_narrative(
    name: str, score: float, txn_count: int, gmv: float,
    coupon_rate: float, return_rate: float, age_days: int
) -> str:
    reasons = []

    if txn_count < 10:
        reasons.append(f"a limited purchase history of only {txn_count} transaction(s)")
    if gmv < 2000:
        reasons.append(f"a total spending of ₹{gmv:,.0f}, which is below our threshold")
    if return_rate > 0.10:
        reasons.append(f"a return rate of {return_rate*100:.0f}%, indicating higher-than-average returns")
    if age_days < 30:
        reasons.append(f"a relatively new account ({age_days} days)")

    if not reasons:
        reasons.append("your overall credit signals not meeting our minimum criteria at this time")

    reason_text = ", ".join(reasons[:-1]) + (f", and {reasons[-1]}" if len(reasons) > 1 else reasons[0])

    return (
        f"Hi {name}, we were unable to approve your BNPL request at this time "
        f"(score: {score:.0f}/100). This is due to {reason_text}. "
        f"We recommend continuing to shop on GrabOn to build a stronger purchase history. "
        f"Your eligibility will be re-evaluated automatically on your next checkout."
    )


def _approval_narrative(
    name: str, score: float, limit: float, breakdown: ScoreBreakdown,
    txn_count: int, gmv: float, coupon_rate: float,
    return_rate: float, categories: int, age_days: int
) -> str:
    strengths = []

    if breakdown.purchase_frequency >= 70:
        strengths.append(f"made {txn_count} purchases, showing strong platform engagement")
    elif breakdown.purchase_frequency >= 40:
        strengths.append(f"maintained consistent shopping activity with {txn_count} transactions")

    if breakdown.deal_redemption >= 70:
        strengths.append(f"used coupons in {coupon_rate*100:.0f}% of transactions, demonstrating smart deal usage")

    if breakdown.gmv_growth >= 70:
        strengths.append(f"shown a healthy spending trajectory with ₹{gmv:,.0f} total GMV")
    elif breakdown.gmv_growth >= 40:
        strengths.append(f"demonstrated consistent spending with ₹{gmv:,.0f} total GMV")

    if breakdown.category_diversification >= 60:
        strengths.append(f"shopped across {categories} different categories")

    if breakdown.return_behavior >= 80:
        rate_text = f"only {return_rate*100:.1f}%" if return_rate > 0 else "no"
        strengths.append(f"maintained {rate_text} returns, reflecting purchase reliability")

    if not strengths:
        strengths.append("met our baseline eligibility criteria")

    strength_text = ". You've ".join(strengths)

    return (
        f"Great news, {name}! You qualify for Buy Now, Pay Later with a credit score of "
        f"{score:.0f}/100 and a limit of ₹{limit:,.0f}. You've {strength_text}. "
        f"Your {age_days}-day account history provides additional confidence. "
        f"Choose your preferred EMI tenure below to complete your purchase."
    )
