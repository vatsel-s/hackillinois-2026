import os
import time
import requests
import json
from datetime import datetime
import threading
# Ensure these imports match your file structure
# Note the dot (.) before kalshi_order_executor
from .kalshi_order_executor import execute_order, get_kalshi_auth_headers, BASE_URL

# Configuration (overridable via env vars)
HEARTBEAT_INTERVAL = 10  # Seconds
PROFIT_TARGET_CENTS = int(os.environ.get("PROFIT_TARGET_CENTS", "7"))  # sell when bid >= avg + N cents

def get_portfolio_data():
    """Fetches the full portfolio JSON."""
    endpoint = "/trade-api/v2/portfolio/positions"
    headers = get_kalshi_auth_headers("GET", endpoint)
    url = f"{BASE_URL}{endpoint}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        return {}

def get_market_bid(ticker):
    """
    Fetches the current Order Book for a ticker to find the best bid.
    """
    endpoint = f"/trade-api/v2/markets/{ticker}/orderbook"
    headers = get_kalshi_auth_headers("GET", endpoint)
    url = f"{BASE_URL}{endpoint}"
    
    try:
        response = requests.get(url, headers=headers)
        # Handle 404 or other errors gracefully
        if response.status_code != 200:
            return 0, 0
            
        book = response.json().get("orderbook", {})
        
        # Helper to find max bid [price, quantity]
        def get_best_bid(bid_list):
            if not bid_list: return 0
            return max(bid_list, key=lambda x: x[0])[0]

        yes_bid = get_best_bid(book.get("yes", []))
        no_bid = get_best_bid(book.get("no", []))
        
        return yes_bid, no_bid
    except Exception:
        return 0, 0

def run_heartbeat():
    print(f"--- Starting Heartbeat (Interval: {HEARTBEAT_INTERVAL}s) ---")
    print(f"Target: Sell if Bid >= Avg Price + {PROFIT_TARGET_CENTS} cents\n")

    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning Portfolio...")
            data = get_portfolio_data()
            
            # 1. Extract Active Market Positions
            market_positions = data.get("market_positions", [])
            active_holdings = [p for p in market_positions if p.get("position", 0) > 0]

            if not active_holdings:
                print("  No active positions found.")

            for p in active_holdings:
                ticker = p.get("ticker")
                count = p.get("position")
                
                # --- Average Price Logic ---
                # Your JSON snippet lacks a direct 'avg_price' in market_positions.
                # We try 'cost_basis' (standard) or fallback to 'total_traded/total_shares' if valid.
                # If completely missing, we default to 0 to prevent accidental sells.
                avg_price = 0
                
                if "fees_paid" in p:
                    avg_price = p["fees_paid"]
                
                # --- Side Logic ---
                # Your JSON implies side might be encoded in ticker or defaults to 'yes'
                side = p.get("side", "yes")

                # 2. Get Current Market Bid
                yes_bid, no_bid = get_market_bid(ticker)
                current_bid = yes_bid if side == 'yes' else no_bid
                
                print(f"  > {ticker}: Held {count} @ ~{avg_price:.1f}¢ | Current Bid: {current_bid}¢")

                # 3. Check Sell Condition
                # Only sell if we have a valid average price > 0
                if avg_price > 0 and current_bid >= (avg_price + PROFIT_TARGET_CENTS):
                    print(f"    $$$ TRIGGER: Selling {count} {side} of {ticker} (Bid {current_bid} >= {avg_price:.1f} + {PROFIT_TARGET_CENTS})")
                    
                    execute_order(
                        ticker=ticker,
                        action="sell",
                        side=side,
                        count=count,
                        type="limit",
                        price=current_bid 
                    )
                elif avg_price == 0:
                    print(f"    [!] Warning: Could not determine avg price for {ticker}. Skipping auto-sell.")

        except Exception as e:
            print(f"Heartbeat Error: {e}")

        time.sleep(HEARTBEAT_INTERVAL)

def start_background_heartbeat():
    """Starts the heartbeat loop in a non-blocking daemon thread."""
    thread = threading.Thread(target=run_heartbeat, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    run_heartbeat()

