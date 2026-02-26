"""
Fraud Detection Service.

Implements velocity-based fraud checks:
- Account age < 7 days → auto-flag
- Redis-cached fraud flags for real-time lookup
"""

import logging
from datetime import datetime

from app.models.user import User
from app.core.config import get_settings
from app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)
settings = get_settings()


class FraudDetectionService:
    """Fraud velocity checks for new user detection."""

    @staticmethod
    def check_velocity(user: User) -> dict:
        """
        Check if a user triggers fraud velocity rules.
        Returns:
            {
                "flagged": bool,
                "reason": str | None,
                "days_since_registration": int,
                "risk_level": "high" | "medium" | "low"
            }
        """
        # Check Redis cache first
        cache_key = f"fraud:velocity:{user.user_id}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        days = (datetime.now() - user.registration_date).days

        if days < settings.FRAUD_VELOCITY_DAYS:
            result = {
                "flagged": True,
                "reason": f"Account age is only {days} day(s) — below the {settings.FRAUD_VELOCITY_DAYS}-day threshold",
                "days_since_registration": days,
                "risk_level": "high",
            }
        elif days < 30:
            result = {
                "flagged": False,
                "reason": None,
                "days_since_registration": days,
                "risk_level": "medium",
            }
        else:
            result = {
                "flagged": False,
                "reason": None,
                "days_since_registration": days,
                "risk_level": "low",
            }

        # Cache result for 5 minutes
        cache_set(cache_key, result, ttl=300)

        if result["flagged"]:
            logger.warning(f"Fraud velocity triggered for user {user.user_id}: {result['reason']}")

        return result
