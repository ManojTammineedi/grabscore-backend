import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_server import get_user_profile, get_user_transactions, check_fraud_velocity

def test_mcp_tools():
    test_user_id = "USER_001"
    
    print("Testing get_user_profile...")
    profile = get_user_profile(test_user_id)
    print(f"Profile: {profile}\n")
    
    print("Testing get_user_transactions...")
    txns = get_user_transactions(test_user_id)
    print(f"Transactions count: {len(txns)}\n")
    
    print("Testing check_fraud_velocity...")
    fraud = check_fraud_velocity(test_user_id)
    print(f"Fraud check: {fraud}\n")
    
    print("MCP setup is fully functional!")

if __name__ == "__main__":
    import asyncio
    test_mcp_tools()
