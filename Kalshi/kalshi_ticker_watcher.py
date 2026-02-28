import asyncio
import websockets
import json
import datetime
from kalshi_auth import (
    sign_pss_text, 
    load_private_key_from_env, 
    KALSHI_API_KEY, 
    KALSHI_PRIVATE_KEY_STR
)

async def start_ticker_stream(tickers_to_watch):
    ws_url = "wss://demo-api.kalshi.co/trade-api/ws/v2"
    path = '/trade-api/ws/v2'
    method = "GET"
    
    # Generate Auth for Handshake
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    msg = timestamp + method + path
    priv_key = load_private_key_from_env(KALSHI_PRIVATE_KEY_STR)
    headers = {
        "KALSHI-ACCESS-KEY": KALSHI_API_KEY,
        "KALSHI-ACCESS-SIGNATURE": sign_pss_text(priv_key, msg),
        "KALSHI-ACCESS-TIMESTAMP": timestamp
    }

    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        print(f"✅ Connected. Monitoring: {tickers_to_watch}")

        # V2 Subscription Command
        sub_payload = {
            "id": 1,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"],
                "market_tickers": tickers_to_watch
            }
        }
        await ws.send(json.dumps(sub_payload))
        
        async for message in ws:
            data = json.loads(message)
            if data.get("type") == "ticker":
                ticker_data = data.get("msg", {})
                symbol = ticker_data.get("market_ticker")
                yes_bid = ticker_data.get("yes_bid")
                yes_ask = ticker_data.get("yes_ask")
                print(f"[{symbol}] BID: {yes_bid}¢ | ASK: {yes_ask}¢")

if __name__ == "__main__":
    # Add any tickers you want to track here
    WATCHLIST = ["KXFED", "CPI-26MAR-T3.1"] 
    asyncio.run(start_ticker_stream(WATCHLIST))