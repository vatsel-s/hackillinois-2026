# market_utils.py
import requests
from .kalshi_order_executor import get_kalshi_auth_headers, BASE_URL

def get_best_ask(ticker, side):
    """
    Fetches the lowest price sellers are willing to accept (Ask) for a specific side.
    Used for IMMEDIATE BUY execution.
    """
    endpoint = f"/trade-api/v2/markets/{ticker}/orderbook"
    headers = get_kalshi_auth_headers("GET", endpoint)
    url = f"{BASE_URL}{endpoint}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
            
        book = response.json().get("orderbook", {})
        
        # Select the correct book side
        # If we want to BUY YES, we look at the YES Asks.
        target_book = book.get(side, [])
        
        if not target_book:
            return None
            
        # Asks are sorted low-to-high. The best price for us (buyer) is the lowest one.
        # Structure: [[price, quantity], [price, quantity]]
        best_ask = target_book[0][0] 
        return best_ask

    except Exception as e:
        print(f"[market] Error fetching ask for {ticker}: {e}")
        return None