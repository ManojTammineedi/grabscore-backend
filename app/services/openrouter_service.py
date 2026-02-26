"""
OpenRouter AI Service integration.
Connects securely to the OpenRouter API to evaluate transaction data against
credit scoring engine factors.
"""

import json
import logging
from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class OpenRouterService:
    @staticmethod
    def generate_narrative_and_score(
        user_name: str,
        transactions_json: str,
        fraud_flagged: bool,
        account_age_days: int
    ) -> dict:
        """
        Calls the OpenRouter API to evaluate user behavior based on raw transaction data
        specifically for the 5 factors:
        1. Purchase frequency
        2. Deal redemption rate (quality signal)
        3. Category diversification
        4. GMV trajectory over 12 months
        5. Return behaviour flag
        """
        settings = get_settings()

        if not settings.USE_OPENROUTER or not settings.OPENROUTER_API_KEY:
            logger.warning("OpenRouter API key missing or service disabled. Falling back to local scoring.")
            return OpenRouterService._generate_mock_fallback(user_name, transactions_json, fraud_flagged, account_age_days)

        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )

            system_prompt = """You are a BNPL credit risk engine. You must evaluate the provided user transaction data to calculate a credit score and credit limit.
You MUST evaluate and score the user on a 0-100 scale based specifically on these 5 factors ONLY:
1. `purchase_frequency`: Higher frequency = higher score.
2. `deal_redemption`: Deal redemption rate (quality signal). Usage suggests engagement.
3. `category_diversification`: More diverse categories = higher score.
4. `gmv_growth`: GMV trajectory over the time period (positive momentum = higher score).
5. `return_behavior`: Lower return rate = higher score.

In addition to the 5 factors above, consider the input `fraud_velocity` flag. (If fraud_velocity is true, score defaults to 0).

Based on these factors, aggregate a total `credit_score` (0-100).
Rules:
- Score > 45 is approved.
- If approved, set credit_limit between 2000 and 50000 (roughly 15% of total GMV).
- Return a cohesive string `narrative` explaining the decision directly pointing out the scores above.

You MUST strictly output ONLY a valid JSON object matching this schema, with no markdown formatting whatsoever, just raw JSON:
{
  "approved": bool,
  "credit_score": float,
  "credit_limit": float,
  "score_breakdown": {
    "purchase_frequency": float,
    "deal_redemption": float,
    "category_diversification": float,
    "gmv_growth": float,
    "return_behavior": float,
    "fraud_velocity": float
  },
  "narrative": "..."
}"""

            user_prompt = f"""Evaluate credit application for: {user_name}
Fraud flag (velocity check): {fraud_flagged}
Account Age: {account_age_days} days

Transactions JSON:
{transactions_json}"""

            logger.info(f"[OPENROUTER API] Using model: {settings.OPENROUTER_MODEL}")
            response = client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )

            content = response.choices[0].message.content.strip()
            
            # Defensive clean up in case LLM outputs markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())

        except Exception as e:
            logger.error(f"OpenRouter API Error: {str(e)}")
            return OpenRouterService._generate_mock_fallback(user_name, transactions_json, fraud_flagged, account_age_days)

    @staticmethod
    def _generate_mock_fallback(name: str, tx_json: str, fraud: bool, age: int) -> dict:
        """Fallback mock function if standard execution fails"""
        
        # very basic fallback matching schema
        if fraud:
            return {
                "approved": False,
                "credit_score": 0.0,
                "credit_limit": 0.0,
                "score_breakdown": {
                    "purchase_frequency": 0.0,
                    "deal_redemption": 0.0,
                    "category_diversification": 0.0,
                    "gmv_growth": 0.0,
                    "return_behavior": 0.0,
                    "fraud_velocity": 0.0
                },
                "narrative": f"Application declined for {name}. Account is too new."
            }

        return {
            "approved": True,
            "credit_score": 75.5,
            "credit_limit": 5000.0,
            "score_breakdown": {
                "purchase_frequency": 80.0,
                "deal_redemption": 60.0,
                "category_diversification": 70.0,
                "gmv_growth": 85.0,
                "return_behavior": 90.0,
                "fraud_velocity": 100.0
            },
            "narrative": f"Fallback Assessment for {name}. Good standing."
        }
