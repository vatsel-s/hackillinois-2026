import requests
import datetime
import json
from uuid import uuid4
from kalshi_auth import (
    sign_pss_text, 
    load_private_key_from_env, 
    KALSHI_API_KEY, 
    KALSHI_PRIVATE_KEY_STR
)

def place_limit_order(ticker, side, count, price_cents):
    """
    side: 'yes' or 'no'
    price_cents: 1-99
    """
    url = "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders"
    method = "POST"
    
    # Order Details
    order_data = {
        "action": "buy",
        "client_order_id": str(uuid4()),
        "count": count,
        "market_ticker": ticker,
        "price": price_cents,
        "side": side,
        "type": "limit"
    }
    body_str = json.dumps(order_data)

    # Signature for POST: timestamp + method + path + body
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    msg = timestamp + method + "/portfolio/orders" + body_str
    
    priv_key = load_private_key_from_env(KALSHI_PRIVATE_KEY_STR)
    headers = {
        "KALSHI-ACCESS-KEY": KALSHI_API_KEY,
        "KALSHI-ACCESS-SIGNATURE": sign_pss_text(priv_key, msg),
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=body_str)
    
    if response.status_code == 201:
        print(f"🚀 SUCCESS: Bought {count} {side} on {ticker} at {price_cents}¢")
        return response.json()
    else:
        print(f"❌ FAILED: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    # Test Trade
    place_limit_order("KXFED", "yes", 1, 45)