"""
Gemini AI Service integration.
Connects directly to the Google Gemini API (Flash) to evaluate transaction data
against credit scoring engine factors.
"""

import json
import logging
import hashlib
import google.generativeai as genai

from app.core.config import get_settings
from app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)

class GeminiService:
    @staticmethod
    def generate_narrative_and_score(
        user_name: str,
        transactions_json: str,
        fraud_flagged: bool,
        account_age_days: int
    ) -> dict:
        """
        Calls the Google Gemini API to evaluate user behavior based on raw transaction data
        specifically for the 5 factors.
        Includes a caching layer based on the hash of the input data.
        """
        settings = get_settings()

        # 1. Generate a unique fingerprint for this specific input set
        fingerprint_data = f"{user_name}|{fraud_flagged}|{account_age_days}|{transactions_json}"
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
        cache_key = f"gemini:assessment:v1:{fingerprint}"

        # 2. Check cache first
        cached_result = cache_get(cache_key)
        if cached_result:
            logger.info(f"[GEMINI CACHE] Found cached result for {user_name} (hash: {fingerprint[:8]}...)")
            return cached_result

        # 3. Fallback/Disabled checks
        if not settings.USE_GEMINI or not settings.GEMINI_API_KEY:
            logger.warning("Gemini API key missing or service disabled. Falling back to mock scoring.")
            return GeminiService._generate_mock_fallback(user_name, transactions_json, fraud_flagged, account_age_days)

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)

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

            logger.info(f"[GEMINI API] Calling {settings.GEMINI_MODEL} for {user_name}...")
            
            # Use generation_config to ensure JSON output if supported, 
            # though the prompt is already very strict.
            response = model.generate_content(
                f"{system_prompt}\n\n{user_prompt}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )

            content = response.text.strip()
            
            # Defensive clean up in case LLM outputs markdown code blocks despite mime_type
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            result = json.loads(content.strip())
            
            # 4. Cache the successful result (24h TTL)
            cache_set(cache_key, result, ttl=86400)
            
            return result

        except Exception as e:
            logger.error(f"Gemini API Error: {str(e)}")
            return GeminiService._generate_mock_fallback(user_name, transactions_json, fraud_flagged, account_age_days)

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
