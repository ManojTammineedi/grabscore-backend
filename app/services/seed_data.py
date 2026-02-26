"""
Database Seed Script.

Seeds 5 user personas with realistic transaction histories:
1. New User       – 3 days old, 0 transactions → fraud velocity reject
2. Casual Shopper – 8 transactions, low GMV, single category
3. Deal Hunter    – 45 transactions, 85% coupon rate, moderate GMV
4. Regular User   – 90 transactions, consistent monthly spend
5. Power User     – 200+ transactions, diversified categories, high GMV growth
"""

import uuid
import random
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Fixed UUIDs for deterministic demo
PERSONAS = {
    "new_user": {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "name": "Rahul Verma",
        "email": "rahul.verma@example.com",
        "risk_segment": "new_user",
        "days_ago": 3,
        "transactions": [],
    },
    "casual_shopper": {
        "user_id": "22222222-2222-2222-2222-222222222222",
        "name": "Priya Sharma",
        "email": "priya.sharma@example.com",
        "risk_segment": "casual_shopper",
        "days_ago": 200,
        "transactions": {
            "count": 8,
            "categories": ["Electronics"],
            "merchants": ["Flipkart"],
            "gmv_range": (200, 1500),
            "coupon_rate": 0.25,
            "return_rate": 0.0,
            "spread_days": 180,
        },
    },
    "deal_hunter": {
        "user_id": "33333333-3333-3333-3333-333333333333",
        "name": "Amit Patel",
        "email": "amit.patel@example.com",
        "risk_segment": "deal_hunter",
        "days_ago": 400,
        "transactions": {
            "count": 45,
            "categories": ["Electronics", "Fashion", "Food & Dining", "Travel"],
            "merchants": ["Amazon", "Myntra", "Swiggy", "MakeMyTrip", "Flipkart"],
            "gmv_range": (150, 3000),
            "coupon_rate": 0.85,
            "return_rate": 0.04,
            "spread_days": 365,
        },
    },
    "regular_user": {
        "user_id": "44444444-4444-4444-4444-444444444444",
        "name": "Sneha Reddy",
        "email": "sneha.reddy@example.com",
        "risk_segment": "regular_user",
        "days_ago": 600,
        "transactions": {
            "count": 90,
            "categories": ["Electronics", "Fashion", "Grocery", "Health", "Food & Dining", "Home"],
            "merchants": ["Amazon", "Myntra", "BigBasket", "PharmEasy", "Zomato", "Pepperfry"],
            "gmv_range": (200, 5000),
            "coupon_rate": 0.55,
            "return_rate": 0.02,
            "spread_days": 365,
        },
    },
    "power_user": {
        "user_id": "55555555-5555-5555-5555-555555555555",
        "name": "Vikram Iyer",
        "email": "vikram.iyer@example.com",
        "risk_segment": "power_user",
        "days_ago": 900,
        "transactions": {
            "count": 210,
            "categories": [
                "Electronics", "Fashion", "Grocery", "Travel", "Food & Dining",
                "Health", "Home", "Entertainment", "Fitness", "Auto"
            ],
            "merchants": [
                "Amazon", "Flipkart", "Myntra", "MakeMyTrip", "Swiggy",
                "Zomato", "BigBasket", "Croma", "Nykaa", "Urban Company"
            ],
            "gmv_range": (300, 8000),
            "coupon_rate": 0.65,
            "return_rate": 0.015,
            "spread_days": 365,
            "growth_bias": True,  # Second half has higher GMV
        },
    },
}

PAYMENT_MODES = ["UPI", "Card", "Wallet", "COD"]


def seed_database(db: Session) -> None:
    """
    Seeds the database with 5 user personas and their transaction histories.
    Skips seeding if users already exist.
    """
    existing = db.query(User).count()
    if existing > 0:
        logger.info(f"Database already has {existing} users, skipping seed")
        return

    logger.info("Seeding database with 5 user personas...")
    random.seed(42)  # Deterministic for demo reproducibility

    for persona_key, config in PERSONAS.items():
        # Create user
        reg_date = datetime.now() - timedelta(days=config["days_ago"])
        user = User(
            user_id=config["user_id"],
            name=config["name"],
            email=config["email"],
            registration_date=reg_date,
            risk_segment=config["risk_segment"],
        )
        db.add(user)

        # Create transactions
        txn_config = config["transactions"]
        if isinstance(txn_config, list):
            # New user: no transactions
            continue

        _generate_transactions(db, user.user_id, txn_config)

    db.commit()
    logger.info("Database seeded successfully with 5 personas")


def _generate_transactions(db: Session, user_id: str, config: dict) -> None:
    """Generate realistic transaction records for a persona."""
    count = config["count"]
    categories = config["categories"]
    merchants = config["merchants"]
    gmv_min, gmv_max = config["gmv_range"]
    coupon_rate = config["coupon_rate"]
    return_rate = config["return_rate"]
    spread_days = config["spread_days"]
    growth_bias = config.get("growth_bias", False)

    for i in range(count):
        # Spread transactions over the time range
        days_offset = random.uniform(0, spread_days)
        txn_date = datetime.now() - timedelta(days=days_offset)

        # GMV with growth bias: recent transactions have higher values
        if growth_bias and days_offset < spread_days / 2:
            gmv = random.uniform(gmv_min * 1.5, gmv_max * 1.3)
        else:
            gmv = random.uniform(gmv_min, gmv_max)

        txn = Transaction(
            transaction_id=str(uuid.uuid4()),
            user_id=user_id,
            merchant_id=random.choice(merchants),
            category=random.choice(categories),
            gmv_amount=round(gmv, 2),
            coupon_used=random.random() < coupon_rate,
            payment_mode=random.choice(PAYMENT_MODES),
            return_flag=random.random() < return_rate,
            transaction_timestamp=txn_date,
        )
        db.add(txn)
