"""
pipeline.py — Main async pipeline orchestrator.

Architecture:
                                         ┌─────────────────────────────┐
  ┌──────────────┐                       │         NLP WORKERS          │
  │  Alpaca WS   │──┐                    │                              │
  └──────────────┘  │                   │  Stage 1: score_headline()   │
  ┌──────────────┐  │  asyncio.Queue    │  ↓ (fast, ~1ms)             │
  │  RSS Poller  │──┼─►  [events] ────►│  Keyword match               │
  └──────────────┘  │                   │  VADER / FinBERT headline    │
  ┌──────────────┐  │                   │                              │
  │ GDELT Poller │──┘                   │  Stage 2 (async):            │
  └──────────────┘                      │  Fetch full article text     │
                                         │  FinBERT (local or Modal)    │
                                         │  → KalshiSignal output       │
                                         └─────────────────────────────┘

Run: python pipeline.py
"""

import asyncio
import logging
import signal as sys_signal
import sys
from datetime import datetime

import httpx

import config
from ingestion import alpaca_ws, rss_poller, gdelt_poller
from nlp import scorer
from nlp.article_fetcher import fetch_article_text
from signal.kalshi_signal import generate_signals, KalshiSignal
from utils.models import DeduplicationCache, NewsEvent

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log"),
    ],
)
logger = logging.getLogger("pipeline")


# ── Stats ─────────────────────────────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.total_received = 0
        self.total_scored = 0
        self.total_signals = 0
        self.by_source: dict[str, int] = {}
        self.started_at = datetime.now()

    def record(self, event: NewsEvent, signal_count: int):
        self.total_received += 1
        if event.headline_sentiment is not None:
            self.total_scored += 1
        self.total_signals += signal_count
        self.by_source[event.source] = self.by_source.get(event.source, 0) + 1

    def report(self):
        elapsed = (datetime.now() - self.started_at).total_seconds()
        rate = self.total_received / max(elapsed / 60, 1)
        logger.info(
            f"📊 Stats: {self.total_received} events "
            f"({rate:.1f}/min) | {self.total_signals} signals | "
            f"sources={self.by_source}"
        )


# ── Signal output hook ────────────────────────────────────────────────────────
# Replace this function with your Kalshi order placement logic.
async def on_signal(signal: KalshiSignal):
    """
    Called whenever a tradeable signal is generated.
    Hook your Kalshi API calls here.
    """
    logger.info(f"🚨 {signal}")
    # Example: place a Kalshi order
    # await kalshi_client.place_order(
    #     market_ticker=signal.market_category,
    #     side=signal.direction,
    #     count=compute_size(signal.confidence),
    # )


# ── NLP Processing Worker ─────────────────────────────────────────────────────
async def nlp_worker(
    queue: asyncio.Queue,
    stats: Stats,
    http_client: httpx.AsyncClient,
    worker_id: int,
):
    """
    Pulls events from the shared queue and runs the two-stage NLP pipeline.
    Multiple workers run concurrently for throughput.
    """
    logger.info(f"NLP worker #{worker_id} started")

    while True:
        event: NewsEvent = await queue.get()

        try:
            # ── Stage 1: Headline scoring (~1ms) ──────────────────────────────
            event = scorer.score_headline(event)

            signals = []

            if scorer.is_tradeable(event):
                # ── Stage 2: Deep article scoring (async, ~50–200ms) ──────────
                if config.NLP_ARTICLE_MODE == "deep" and event.full_text is None:
                    # Fetch full article text if we don't already have it
                    text = await fetch_article_text(event.url, http_client)
                    if text:
                        event.full_text = text

                if event.full_text:
                    event = await scorer.score_article_async(event)

                # ── Generate Kalshi signals ───────────────────────────────────
                signals = generate_signals(event)
                for sig in signals:
                    await on_signal(sig)

            stats.record(event, len(signals))

            # Log everything that matched a Kalshi market (even below threshold)
            if event.matched_markets:
                logger.debug(str(event))

        except Exception as e:
            logger.error(f"NLP worker #{worker_id} error: {e}", exc_info=True)
        finally:
            queue.task_done()


# ── Periodic stats reporter ───────────────────────────────────────────────────
async def stats_reporter(stats: Stats, interval: int = 60):
    while True:
        await asyncio.sleep(interval)
        stats.report()


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    logger.info("=" * 60)
    logger.info("🚀 Kalshi News Pipeline starting...")
    logger.info(f"   NLP headline mode : {config.NLP_HEADLINE_MODE}")
    logger.info(f"   NLP article mode  : {config.NLP_ARTICLE_MODE}")
    logger.info(f"   Min signal score  : {config.NLP_MIN_SIGNAL_SCORE}")
    logger.info(f"   Markets tracked   : {list(config.KALSHI_MARKET_KEYWORDS.keys())}")
    logger.info("=" * 60)

    # Shared state
    event_queue = asyncio.Queue(maxsize=config.EVENT_QUEUE_MAXSIZE)
    dedup = DeduplicationCache(maxsize=config.DEDUP_WINDOW_SIZE)
    stats = Stats()

    # Shared HTTP client for article fetching
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as http_client:

        # Graceful shutdown on CTRL+C
        shutdown_event = asyncio.Event()

        def _shutdown(signum, frame):
            logger.info("Shutdown signal received — stopping pipeline...")
            shutdown_event.set()

        sys_signal.signal(sys_signal.SIGINT, _shutdown)
        sys_signal.signal(sys_signal.SIGTERM, _shutdown)

        # ── Launch all coroutines ─────────────────────────────────────────────
        tasks = [
            # Ingestors
            asyncio.create_task(alpaca_ws.run(event_queue, dedup),   name="alpaca_ws"),
            asyncio.create_task(rss_poller.run(event_queue, dedup),  name="rss"),
            asyncio.create_task(gdelt_poller.run(event_queue, dedup), name="gdelt"),

            # NLP workers (run 4 concurrently for throughput)
            *[
                asyncio.create_task(
                    nlp_worker(event_queue, stats, http_client, i),
                    name=f"nlp_worker_{i}",
                )
                for i in range(4)
            ],

            # Periodic stats report every 60s
            asyncio.create_task(stats_reporter(stats), name="stats"),
        ]

        logger.info(f"✅ {len(tasks)} tasks running. Listening for news...")

        # Wait until shutdown signal
        await shutdown_event.wait()

        # Cancel all tasks
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    stats.report()
    logger.info("Pipeline stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())