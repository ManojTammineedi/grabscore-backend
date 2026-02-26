from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session
from contextlib import contextmanager

# Import standard app components
from app.core.database import SessionLocal
from app.models.user import User
from app.models.transaction import Transaction

# Create an MCP server instance
mcp = FastMCP("GrabOn-Data-Server")

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@mcp.tool()
def get_user_profile(user_id: str) -> dict:
    """Retrieve demographic and risk segment data for a user."""
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"error": "User not found"}
        return {
            "user_id": user.user_id,
            "name": user.name,
            "registration_date": user.registration_date.isoformat(),
            "risk_segment": user.risk_segment,
        }

@mcp.tool()
def get_user_transactions(user_id: str) -> list[dict]:
    """Retrieve the full 12-month transaction history for a user."""
    with get_db() as db:
        transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
        
        # Calculate frequency (transactions per month roughly, or just total count for now as a simple metric)
        # Note: A simple frequency metric based on the count over the time span of transactions.
        if transactions:
            import datetime
            dates = [t.transaction_timestamp for t in transactions]
            min_date, max_date = min(dates), max(dates)
            days = (max_date - min_date).days
            frequency_per_month = (len(transactions) / (days / 30.0)) if days > 0 else len(transactions)
        else:
            frequency_per_month = 0.0

        return [
            {
                "transaction_id": t.transaction_id,
                "merchant": t.merchant_id,
                "category": t.category,
                "GMV": t.gmv_amount,
                "coupon_used": t.coupon_used,
                "payment_mode": t.payment_mode,
                "return_flag": t.return_flag,
                "date": t.transaction_timestamp.isoformat(),
                "frequency": round(frequency_per_month, 2)
            }
            for t in transactions
        ]

@mcp.tool()
def check_fraud_velocity(user_id: str) -> dict:
    """Check fraud velocity signals for a user, such as account age < 7 days."""
    from datetime import datetime
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        age_days = (datetime.now() - user.registration_date).days
        flagged = age_days < 7
        return {
            "user_id": user.user_id,
            "account_age_days": age_days,
            "fraud_velocity_flagged": flagged,
            "reason": "Account is younger than 7 days" if flagged else "Account maturity check passed"
        }

if __name__ == "__main__":
    # Start the standard streaming stdio server
    print("Starting GrabOn Data MCP Server on stdio...")
    mcp.run()
