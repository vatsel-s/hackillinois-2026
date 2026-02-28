"""
ingestion/alpaca_ws.py — Real-time Benzinga news via Alpaca WebSocket.

Gives ~130+ financial headlines/day pushed in real-time.
Best source for market-moving financial events (Fed, earnings, macro).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import websockets

from config import ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_NEWS_WS
from utils.models import NewsEvent, DeduplicationCache, make_uid

logger = logging.getLogger("alpaca_ws")


async def run(queue: asyncio.Queue, dedup: DeduplicationCache):
    """
    Maintain a persistent WebSocket connection to Alpaca's news stream.
    Auto-reconnects on disconnect with exponential backoff.
    """
    backoff = 1
    while True:
        try:
            await _connect(queue, dedup)
            backoff = 1  # reset on clean disconnect
        except Exception as e:
            logger.warning(f"Alpaca WS error: {e}. Reconnecting in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


async def _connect(queue: asyncio.Queue, dedup: DeduplicationCache):
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_API_SECRET,
    }

    async with websockets.connect(ALPACA_NEWS_WS, additional_headers=headers) as ws:
        logger.info("Alpaca WS: connected")

        # Authenticate
        auth_msg = json.dumps({"action": "auth", "key": ALPACA_API_KEY, "secret": ALPACA_API_SECRET})
        await ws.send(auth_msg)

        # Subscribe to ALL news (wildcard)
        sub_msg = json.dumps({"action": "subscribe", "news": ["*"]})
        await ws.send(sub_msg)
        logger.info("Alpaca WS: subscribed to all news")

        async for raw in ws:
            messages = json.loads(raw)
            if not isinstance(messages, list):
                messages = [messages]

            for msg in messages:
                msg_type = msg.get("T")

                if msg_type == "n":  # news article
                    _handle_article(msg, queue, dedup)
                elif msg_type == "error":
                    logger.error(f"Alpaca WS error message: {msg}")
                elif msg_type in ("success", "subscription"):
                    logger.debug(f"Alpaca WS control: {msg}")


def _handle_article(msg: dict, queue: asyncio.Queue, dedup: DeduplicationCache):
    uid = make_uid(msg.get("url") or msg.get("headline", ""))
    if not dedup.is_new(uid):
        return

    try:
        published_at = datetime.fromisoformat(
            msg["created_at"].replace("Z", "+00:00")
        )
    except Exception:
        published_at = datetime.now(timezone.utc)

    event = NewsEvent(
        uid=uid,
        source="alpaca",
        headline=msg.get("headline", ""),
        url=msg.get("url", ""),
        published_at=published_at,
        full_text=msg.get("content"),  # Alpaca sometimes includes content
    )

    try:
        queue.put_nowait(event)
        logger.debug(f"Alpaca → queue: {event.headline[:60]}")
    except asyncio.QueueFull:
        logger.warning("Event queue full — dropping Alpaca article")