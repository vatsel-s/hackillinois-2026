"""
ingestion/rss_poller.py — Async RSS feed poller for 13+ major news outlets.

Polls all configured RSS feeds concurrently every RSS_POLL_INTERVAL seconds.
Gives thousands of articles/day with ~30–60s latency behind publication.
"""

import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser
import httpx

from config import RSS_FEEDS, RSS_POLL_INTERVAL
from utils.models import NewsEvent, DeduplicationCache, make_uid

logger = logging.getLogger("rss_poller")


async def run(queue: asyncio.Queue, dedup: DeduplicationCache):
    """Poll all RSS feeds in parallel on a fixed interval."""
    logger.info(f"RSS poller: monitoring {len(RSS_FEEDS)} feeds every {RSS_POLL_INTERVAL}s")
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        while True:
            tasks = [_poll_feed(client, url, queue, dedup) for url in RSS_FEEDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for url, result in zip(RSS_FEEDS, results):
                if isinstance(result, Exception):
                    logger.warning(f"RSS error ({url[:40]}): {result}")
            await asyncio.sleep(RSS_POLL_INTERVAL)


async def _poll_feed(
    client: httpx.AsyncClient,
    feed_url: str,
    queue: asyncio.Queue,
    dedup: DeduplicationCache,
):
    """Fetch a single RSS feed and enqueue new articles."""
    response = await client.get(feed_url)
    feed = feedparser.parse(response.text)
    new_count = 0

    for entry in feed.entries:
        url = entry.get("link", "")
        uid = make_uid(url or entry.get("title", ""))

        if not dedup.is_new(uid):
            continue

        headline = entry.get("title", "").strip()
        if not headline:
            continue

        published_at = _parse_date(entry)

        # RSS often includes a short summary — use as lightweight article text
        summary = entry.get("summary", "") or entry.get("description", "")

        event = NewsEvent(
            uid=uid,
            source="rss",
            headline=headline,
            url=url,
            published_at=published_at,
            full_text=summary if len(summary) > 80 else None,
        )

        try:
            queue.put_nowait(event)
            new_count += 1
        except asyncio.QueueFull:
            logger.warning("Event queue full — dropping RSS article")
            break

    if new_count:
        domain = feed_url.split("/")[2]
        logger.debug(f"RSS ({domain}): +{new_count} new articles")


def _parse_date(entry: dict) -> datetime:
    """Parse RSS pubDate into a timezone-aware datetime."""
    for field in ("published", "updated", "created"):
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return datetime.now(timezone.utc)