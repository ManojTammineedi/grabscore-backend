"""
Claude AI Service integration.
Connects securely to the Anthropic API to generate intelligent, data-backed credit narratives.
"""

import os
import json
from anthropic import Anthropic
from pydantic import BaseModel

class ScoreBreakdownData(BaseModel):
    purchase_frequency: float
    deal_redemption: float
    category_diversification: float
    gmv_growth: float
    return_behavior: float
    fraud_velocity: float

class ClaudeService:
    @staticmethod
    def generate_narrative_and_score(
        user_name: str,
        transaction_count: int,
        total_gmv: float,
        coupon_rate: float,
        return_rate: float,
        categories_count: int,
        account_age_days: int,
        fraud_flagged: bool
    ) -> dict:
        """
        Calls the Anthropic Claude API to generate the credit score and narrative.
        Optimized for token efficiency on free/limited accounts.
        """
        from app.core.config import get_settings
        settings = get_settings()
        
        # Check if Claude is enabled and key exists
        if not settings.CLAUDE_ENABLED or not settings.ANTHROPIC_API_KEY:
            return ClaudeService._generate_mock_fallback(
                user_name, transaction_count, total_gmv, coupon_rate, 
                return_rate, categories_count, account_age_days, fraud_flagged
            )

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Compacted prompt for token efficiency
        user_data = {
            "name": user_name,
            "txn": transaction_count,
            "gmv": total_gmv,
            "coupon": f"{coupon_rate:.1%}",
            "return": f"{return_rate:.1%}",
            "cats": categories_count,
            "age": account_age_days,
            "fraud": fraud_flagged
        }

        system_prompt = "You are a BNPL credit engine. Return valid JSON only. Score > 60 is approved. Limit = 10-20% of GMV (max 50k). Narrative must cite user data."
        user_prompt = f"Data: {json.dumps(user_data)}. Schema: {{approved:bool, credit_score:float, credit_limit:float, score_breakdown:{{purchase_frequency:float, deal_redemption:float, category_diversification:float, gmv_growth:float, return_behavior:float, fraud_velocity:float}}, narrative:string}}"
        
        try:
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=500,
                temperature=0,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.content[0].text.strip()
            # Handle potential markdown wrapping
            if content.startswith("```"):
                content = content.splitlines()[1:-1]
                content = "".join(content)
                
            return json.loads(content)

        except Exception as e:
            print(f"Claude API Error: {str(e)}")
            return ClaudeService._generate_mock_fallback(
                user_name, transaction_count, total_gmv, coupon_rate, 
                return_rate, categories_count, account_age_days, fraud_flagged
            )

    @staticmethod
    def _generate_mock_fallback(name: str, tx: int, gmv: float, c_rate: float, 
                                r_rate: float, cat: int, age: int, fraud: bool) -> dict:
        """Local deterministic fallback if API Key is missing or rate limited."""
        if fraud:
            return {
                "approved": False, "credit_score": 0.0, "credit_limit": 0.0,
                "score_breakdown": { "purchase_frequency": 0, "deal_redemption": 0, "category_diversification": 0, "gmv_growth": 0, "return_behavior": 0, "fraud_velocity": 0 },
                "narrative": f"Hi {name}, your account is too new ({age} days). A baseline of 7 days is required for BNPL."
            }
        
        # Simple local scoring mock
        score = min(100.0, (tx * 2) + (c_rate * 20) + (cat * 5) - (r_rate * 50))
        approved = score > 40
        return {
            "approved": approved,
            "credit_score": score,
            "credit_limit": gmv * 0.15 if approved else 0.0,
            "score_breakdown": {
                "purchase_frequency": min(100.0, tx * 5.0),
                "deal_redemption": c_rate * 100,
                "category_diversification": min(100.0, cat * 10.0),
                "gmv_growth": min(100.0, (gmv / 1000) * 10.0),
                "return_behavior": max(0.0, 100 - (r_rate * 200)),
                "fraud_velocity": 100.0
            },
            "narrative": f"Great news, {name}! You qualify based on your strong history of {tx} purchases across {cat} categories." if approved else "Unable to approve based on current purchase history."
        }
