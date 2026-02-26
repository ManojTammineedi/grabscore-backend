"""
EMI Calculator Service.

Generates 3/6/9 month EMI offers based on credit limit and purchase amount.
Simulates PayU LazyPay sandbox response for the prototype.
"""

from app.schemas.credit import EMIOffer
from app.core.config import get_settings

settings = get_settings()


class EMICalculator:
    """Calculate EMI tenure options for approved BNPL transactions."""

    @staticmethod
    def generate_offers(amount: float, credit_limit: float) -> list[EMIOffer]:
        """
        Generate EMI offers for the given amount.
        Only generates offers if the amount is within the credit limit.

        Args:
            amount: Purchase amount
            credit_limit: Approved credit limit

        Returns:
            List of EMIOffer for 3, 6, and 9 month tenures
        """
        if amount > credit_limit or amount <= 0:
            return []

        tenures = [
            (3, settings.EMI_INTEREST_RATE_3M),
            (6, settings.EMI_INTEREST_RATE_6M),
            (9, settings.EMI_INTEREST_RATE_9M),
        ]

        offers = []
        for months, annual_rate in tenures:
            monthly_rate = annual_rate / 12 / 100

            if monthly_rate == 0:
                # No-cost EMI
                monthly_amount = amount / months
                total = amount
            else:
                # Standard EMI formula: P * r * (1+r)^n / ((1+r)^n - 1)
                factor = (1 + monthly_rate) ** months
                monthly_amount = amount * monthly_rate * factor / (factor - 1)
                total = monthly_amount * months

            processing_fee = round(amount * 0.01, 2) if annual_rate > 0 else 0.0

            offers.append(
                EMIOffer(
                    tenure_months=months,
                    monthly_amount=round(monthly_amount, 2),
                    interest_rate=annual_rate,
                    total_amount=round(total, 2),
                    processing_fee=processing_fee,
                )
            )

        return offers
