"""
config.py — Central configuration for the Kalshi news pipeline.

API keys are loaded from a .env file. Copy .env.example → .env and fill in your keys.
Non-secret tuning parameters (feed lists, keywords, thresholds) live here directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Alpaca ────────────────────────────────────────────────────────────────────
ALPACA_API_KEY    = os.environ["ALPACA_API_KEY"]
ALPACA_API_SECRET = os.environ["ALPACA_API_SECRET"]
ALPACA_NEWS_WS    = "wss://stream.data.alpaca.markets/v1beta1/news"

# ── RSS Feeds ─────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    # Politics / World
    "https://feeds.reuters.com/reuters/topNews",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://apnews.com/hub/ap-top-news?format=feed",
    "https://feeds.politico.com/politico/politico-main",
    "https://thehill.com/homenews/feed/",
    "https://www.axios.com/feeds/feed.rss",
    "https://feeds.washingtonpost.com/rss/politics",
    # Economics / Finance
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.bloomberg.com/markets/news.rss",
    # Science / Crypto / Tech (Kalshi has markets here too)
    "https://techcrunch.com/feed/",
    "https://cointelegraph.com/rss",
]
RSS_POLL_INTERVAL = 45  # seconds between polls

# ── GDELT ─────────────────────────────────────────────────────────────────────
GDELT_API_URL      = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_POLL_INTERVAL = 900  # 15 minutes (GDELT updates every 15 min)
GDELT_MAX_RECORDS  = 250

# ── NLP ───────────────────────────────────────────────────────────────────────
# "fast" uses keyword + VADER (no GPU needed, ~1ms per headline)
# "deep" uses FinBERT transformer (better accuracy, ~50–200ms per article)
NLP_HEADLINE_MODE = os.getenv("NLP_HEADLINE_MODE", "fast")   # options: "fast" | "finbert"
NLP_ARTICLE_MODE  = os.getenv("NLP_ARTICLE_MODE", "deep")    # runs async after headline signal fires
NLP_MIN_SIGNAL_SCORE = float(os.getenv("NLP_MIN_SIGNAL_SCORE", "0.35"))

# ── Kalshi Market Keywords ────────────────────────────────────────────────────
# Map Kalshi market categories to the keywords that move them.
# Add/remove based on what contracts you're actively trading.
KALSHI_MARKET_KEYWORDS = {
    "FED_RATE": [
        "federal reserve", "fed rate", "rate hike", "rate cut", "fomc",
        "powell", "basis points", "interest rate", "inflation", "cpi",
        "core pce", "monetary policy", "quantitative",
    ],
    "JOBS": [
        "jobs report", "unemployment", "nonfarm payroll", "labor market",
        "job openings", "jolts", "initial claims", "jobless claims",
    ],
    "ELECTION": [
        "election", "ballot", "candidate", "poll", "primary", "senate",
        "congress", "vote", "democrat", "republican", "president",
        "impeach", "approval rating",
    ],
    "MARKETS": [
        "s&p 500", "dow jones", "nasdaq", "stock market", "recession",
        "gdp", "earnings", "treasury", "yield curve", "10-year",
    ],
    "SPORTS_MLB": [
        "mlb", "baseball", "world series", "no-hitter", "home run record",
    ],
    "SPORTS_NFL": [
        "nfl", "super bowl", "touchdown", "quarterback",
    ],
    "CRYPTO": [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "sec", "etf approval",
    ],
    "GEOPOLITICAL": [
        "war", "sanctions", "ceasefire", "invasion", "nuclear", "nato",
        "russia", "china", "taiwan", "middle east", "oil price", "opec",
    ],
}

# ── Pipeline ──────────────────────────────────────────────────────────────────
EVENT_QUEUE_MAXSIZE = int(os.getenv("EVENT_QUEUE_MAXSIZE", "10000"))
DEDUP_WINDOW_SIZE   = int(os.getenv("DEDUP_WINDOW_SIZE", "50000"))
LOG_LEVEL           = os.getenv("LOG_LEVEL", "INFO")
