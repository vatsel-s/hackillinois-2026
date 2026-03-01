import uuid
import json
import requests
import os
from .kalshi_auth import get_kalshi_auth_headers

# Ensure this matches your environment (Production vs Demo)
BASE_URL = "https://api.elections.kalshi.com" 

def execute_order(ticker: str, action: str, side: str, count: int, type: str = 'limit', price: int = None):
    """
    Executes a trade order on Kalshi.
    
    Args:
        ticker (str): The market ticker (e.g., "KXHIGHLOW-23DEC26-T4000").
        action (str): "buy" or "sell".
        side (str): "yes" or "no".
        count (int): Number of contracts.
        type (str): "limit" or "market". Default is "limit".
        price (int): The price in cents (1-99). Required for limit orders.
    """
    
    # 1. Input Sanitization & Validation
    # Force lowercase to prevent logic errors (e.g., "Yes" vs "yes")
    action = action.lower()
    side = side.lower()
    type = type.lower()

    if type == 'limit' and price is None:
        raise ValueError("Price (in cents) is strictly required for limit orders.")

    # 2. Construct the Base Payload
    payload = {
        "ticker": ticker,
        "action": action,
        "side": side,
        "count": count,
        "type": type,
        "client_order_id": str(uuid.uuid4())
    }

    # 3. Handle Price Mapping (Crucial Step)
    # Kalshi expects strictly one of 'yes_price' or 'no_price' for limit orders
    if type == 'limit':
        if side == 'yes':
            payload["yes_price"] = price
        elif side == 'no':
            payload["no_price"] = price
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'yes' or 'no'.")

    # 4. Prepare Request
    endpoint = "/trade-api/v2/portfolio/orders"
    full_url = f"{BASE_URL}{endpoint}"
    
    # Generate headers (Assuming get_kalshi_auth_headers is defined in your file)
    headers = get_kalshi_auth_headers("POST", endpoint)

    # 5. Execute Request with Debugging
    try:
        response = requests.post(full_url, json=payload, headers=headers)
        response.raise_for_status() # Raise error for 4xx/5xx
        
        data = response.json()
        print(f"Order Placed Successfully: {data.get('order', {}).get('order_id')}")
        return data
        
    except requests.exceptions.HTTPError as e:
        print(f"\n--- HTTP Error {e.response.status_code} ---")
        print(f"Error Details: {e.response.text}")
        print(f"Sent Payload: {json.dumps(payload, indent=2)}") # Debug print
        raise
    except Exception as e:
        print(f"System Error: {e}")
        raise

# --- Usage Example ---
if __name__ == "__main__":
    try:
        # Ensure you use a valid, active ticker. Tickers change daily/weekly.
        # Example: Buying 'Yes' at 50 cents
        order_result = execute_order(
            ticker="KXPRESNOMD-28-KH", # Update this to a currently active ticker!
            action="sell",
            side="yes",
            count=1,
            type="limit",
            price=50
        )
        print(json.dumps(order_result, indent=2))
    except Exception:
        pass