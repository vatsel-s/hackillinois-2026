"""
FastAPI backend for Kalshi News frontend.
Run from repo root: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
import sys
from pathlib import Path

# Allow importing News, Kalshi from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# Optional imports (fail gracefully if missing or env not set)
# -----------------------------------------------------------------------------
def _load_news():
    """Return mock news by default. RSS poll is slow (25+ feeds) and blocks requests."""
    return _mock_news()


def _mock_news():
    from datetime import datetime, timezone
    return [
        {
            "source": "Demo",
            "headline": "Fed signals cautious approach to rate cuts",
            "content_header": "Sample headline for dashboard demo.",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "link": "https://example.com/1",
        },
        {
            "source": "Demo",
            "headline": "Markets digest earnings season",
            "content_header": "Run the RSS pipeline to load real articles.",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "link": "https://example.com/2",
        },
    ]

def _place_order(ticker: str, side: str, count: int, price_cents: int):
    try:
        from Kalshi.kalshi_order_executor import place_limit_order
        result = place_limit_order(ticker, side, count, price_cents)
        if result is None:
            return {"success": False, "error": "Order rejected or API error"}
        return {"success": True, "order_id": result.get("order", {}).get("order_id")}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_sentiment(text: str):
    try:
        import modal
        score_article = modal.Function.from_name("finnews-sentiment", "score-article")
        out = score_article.remote(text)
        # FinBERT returns e.g. {"label": "positive", "score": 0.99}
        label = (out.get("label") or "neutral").lower()
        score = float(out.get("score", 0.5))
        return {"label": label, "score": score}
    except Exception as e:
        return {"label": "neutral", "score": 0.5}

# Default watchlist (from kalshi_ticker_watcher)
DEFAULT_WATCHLIST = [
    "KXFEDCHAIRNOM-29-KW",
    "KXKHAMENEIOUT-AKHA-26JUL01",
]
# Mock ticker data when no live WS
MOCK_TICKERS = [
    {"market_ticker": t, "yes_bid": 45, "yes_ask": 55, "last_updated": 0}
    for t in DEFAULT_WATCHLIST
]

# In-memory ticker cache (could be filled by a background WebSocket client)
ticker_cache: list = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure ticker_cache has something
    if not ticker_cache:
        ticker_cache.extend(MOCK_TICKERS)
    yield
    # Shutdown
    ticker_cache.clear()


app = FastAPI(
    title="Kalshi News API",
    description="Backend for news-driven prediction market dashboard",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request/response models
# -----------------------------------------------------------------------------
class SentimentRequest(BaseModel):
    text: str


class OrderRequest(BaseModel):
    ticker: str
    side: str  # yes | no
    count: int
    price_cents: int


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/api/news")
def api_news(limit: int = 50):
    """Return recent articles from RSS pipeline."""
    articles = _load_news()
    return articles[:limit]


@app.get("/api/tickers")
def api_tickers():
    """Return current ticker snapshots (from cache or mock)."""
    if ticker_cache:
        return ticker_cache
    return MOCK_TICKERS


@app.post("/api/sentiment")
def api_sentiment(body: SentimentRequest):
    """Return FinBERT sentiment for given text (via Modal)."""
    return _get_sentiment(body.text)


@app.post("/api/orders")
def api_orders(body: OrderRequest):
    """Place a limit order on Kalshi (demo API)."""
    if body.side not in ("yes", "no"):
        raise HTTPException(400, "side must be 'yes' or 'no'")
    if body.count < 1 or body.price_cents < 1 or body.price_cents > 99:
        raise HTTPException(400, "Invalid count or price_cents")
    return _place_order(body.ticker, body.side, body.count, body.price_cents)


@app.get("/health")
def health():
    return {"status": "ok"}
