"""
ingestion/gdelt_poller.py — GDELT global news API (no API key required).

Polls hundreds of thousands of global outlets. Updates every 15 minutes.
Used for: macro trend detection, geopolitical signals, volume normalization.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from config import (
    GDELT_API_URL, GDELT_POLL_INTERVAL, GDELT_MAX_RECORDS,
    KALSHI_MARKET_KEYWORDS,
)
from utils.models import NewsEvent, DeduplicationCache, make_uid

logger = logging.getLogger("gdelt_poller")

# Build a combined query from all Kalshi market keywords
# GDELT will return articles mentioning any of these terms
def _build_gdelt_query() -> str:
    all_keywords = []
    for keywords in KALSHI_MARKET_KEYWORDS.values():
        all_keywords.extend(keywords[:2])  # top 2 per market to keep query focused
    # GDELT uses space-separated OR queries by default
    unique = list(dict.fromkeys(all_keywords))[:30]  # cap at 30 terms
    return " OR ".join(f'"{kw}"' for kw in unique)


GDELT_QUERY = _build_gdelt_query()


async def run(queue: asyncio.Queue, dedup: DeduplicationCache):
    """Poll GDELT API every 15 minutes for keyword-matched global news."""
    logger.info(f"GDELT poller: starting (interval={GDELT_POLL_INTERVAL}s)")
    logger.debug(f"GDELT query: {GDELT_QUERY[:120]}...")

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        while True:
            try:
                await _poll(client, queue, dedup)
            except Exception as e:
                logger.warning(f"GDELT poll error: {e}")
            await asyncio.sleep(GDELT_POLL_INTERVAL)


async def _poll(client: httpx.AsyncClient, queue: asyncio.Queue, dedup: DeduplicationCache):
    params = {
        "query": GDELT_QUERY,
        "mode": "artlist",
        "maxrecords": GDELT_MAX_RECORDS,
        "format": "json",
        "timespan": "15min",
        "sourcelang": "English",
    }

    response = await client.get(GDELT_API_URL, params=params)
    data = response.json()
    articles = data.get("articles", [])

    new_count = 0
    for article in articles:
        url = article.get("url", "")
        uid = make_uid(url or article.get("title", ""))
        if not dedup.is_new(uid):
            continue

        headline = article.get("title", "").strip()
        if not headline:
            continue

        published_at = _parse_gdelt_date(article.get("seendate", ""))

        event = NewsEvent(
            uid=uid,
            source="gdelt",
            headline=headline,
            url=url,
            published_at=published_at,
        )

        try:
            queue.put_nowait(event)
            new_count += 1
        except asyncio.QueueFull:
            logger.warning("Event queue full — dropping GDELT article")
            break

    logger.info(f"GDELT: +{new_count} new articles ({len(articles)} total matched)")


def _parse_gdelt_date(raw: str) -> datetime:
    """Parse GDELT's YYYYMMDDTHHMMSSZ format."""
    try:
        return datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)