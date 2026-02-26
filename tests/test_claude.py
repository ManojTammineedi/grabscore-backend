import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.claude_service import ClaudeService
from app.core.config import get_settings

def test_claude():
    settings = get_settings()
    print(f"Claude Enabled: {settings.CLAUDE_ENABLED}")
    print(f"API Key Present: {'Yes' if settings.ANTHROPIC_API_KEY else 'No'}")
    
    result = ClaudeService.generate_narrative_and_score(
        user_name="Test User",
        transaction_count=10,
        total_gmv=10000.0,
        coupon_rate=0.2,
        return_rate=0.05,
        categories_count=5,
        account_age_days=180,
        fraud_flagged=False
    )
    import json
    print("Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_claude()
