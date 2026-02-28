# ticker_stream.py
import asyncio
import websockets
import json
from kalshi_auth import build_auth_headers

WS_URL  = "wss://api.elections.kalshi.com/trade-api/ws/v2"
WS_PATH = "/trade-api/ws/v2"

async def start_ticker_stream(tickers_to_watch: list[str]):
    headers = build_auth_headers("GET", WS_PATH)

    async with websockets.connect(WS_URL, additional_headers=headers) as ws:
        print(f"✅ Connected to PROD. Monitoring: {tickers_to_watch}")

        ticker_key   = "market_ticker"  if len(tickers_to_watch) == 1 else "market_tickers"
        ticker_value = tickers_to_watch[0] if len(tickers_to_watch) == 1 else tickers_to_watch

        sub_payload = {
            "id": 1,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"],
                ticker_key: ticker_value
            }
        }
        await ws.send(json.dumps(sub_payload))

        async for message in ws:
            data     = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "ok":
                print(f"✅ Subscription confirmed: {data.get('msg')}")
            elif msg_type == "error":
                print(f"❌ Server error: {data}")
            elif msg_type == "ticker":
                ticker_data = data.get("msg", {})
                symbol  = ticker_data.get("market_ticker")
                yes_bid = ticker_data.get("yes_bid")
                yes_ask = ticker_data.get("yes_ask")
                print(f"[{symbol}] BID: {yes_bid}¢ | ASK: {yes_ask}¢")
            else:
                print(f"[unhandled type={msg_type}] {data}")

if __name__ == "__main__":
    WATCHLIST = ["KXFEDCHAIRNOM-29-KW", "KXKHAMENEIOUT-AKHA-26JUL01"]
    asyncio.run(start_ticker_stream(WATCHLIST))