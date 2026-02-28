"""
ingestion/reddit_stream.py — Real-time Reddit post stream via PRAW.

True push stream (not polling). Dozens of posts/minute during busy periods.
Best for: social sentiment, breaking news before mainstream outlets, sports.
"""

import asyncio
import logging
from datetime import datetime, timezone

import praw

from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT, REDDIT_SUBREDDITS,
)
from utils.models import NewsEvent, DeduplicationCache, make_uid

logger = logging.getLogger("reddit_stream")


async def run(queue: asyncio.Queue, dedup: DeduplicationCache):
    """
    Run Reddit streaming in a thread pool executor (PRAW is synchronous).
    Streams posts from all configured subreddits simultaneously.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _blocking_stream, queue, dedup, loop)


def _blocking_stream(
    queue: asyncio.Queue,
    dedup: DeduplicationCache,
    loop: asyncio.AbstractEventLoop,
):
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

    subreddit_str = "+".join(REDDIT_SUBREDDITS)
    subreddit = reddit.subreddit(subreddit_str)

    logger.info(f"Reddit stream: listening on r/{subreddit_str[:60]}...")

    # stream.submissions() blocks and yields new posts in real-time
    # skip_existing=True skips the initial backfill on startup
    for post in subreddit.stream.submissions(skip_existing=True):
        uid = make_uid(post.url or post.id)
        if not dedup.is_new(uid):
            continue

        published_at = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)

        event = NewsEvent(
            uid=uid,
            source="reddit",
            headline=post.title,
            url=f"https://reddit.com{post.permalink}",
            published_at=published_at,
            subreddit=post.subreddit.display_name,
            score=post.score,
            # Reddit selftext as article body (for text posts)
            full_text=post.selftext if post.is_self else None,
        )

        # Thread-safe: schedule put on the event loop
        asyncio.run_coroutine_threadsafe(
            _safe_put(queue, event), loop
        )


async def _safe_put(queue: asyncio.Queue, event: NewsEvent):
    try:
        queue.put_nowait(event)
        logger.debug(f"Reddit → queue: [r/{event.subreddit}] {event.headline[:60]}")
    except asyncio.QueueFull:
        logger.warning("Event queue full — dropping Reddit post")