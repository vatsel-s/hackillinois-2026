# news_monitor.py
import feedparser
import pandas as pd
import time
import os
import re
import requests
from datetime import datetime, timedelta, timezone
from rapidfuzz import process, fuzz

# --- CONFIGURATION ---
CSV_FILE       = "news_log.csv"
KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
POLL_INTERVAL  = 20
MARKET_LIMIT   = 1000
MATCH_THRESHOLD = 58   # lower = more matches, higher = more precision

NEWS_FEEDS = {
    "BBC Home":          "https://feeds.bbci.co.uk/news/rss.xml",
    "NYT Home":          "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "NPR":               "https://feeds.npr.org/1001/rss.xml",
    "The Hill":          "https://thehill.com/rss/syndicator/19110",
    "NYT Politics":      "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    "The Hill Politics": "https://thehill.com/homenews/feed",
    "Politico":          "https://www.politico.com/rss/politicopicks.xml",
    "WashPost Politics": "https://feeds.washingtonpost.com/rss/politics",
    "CNBC Business":     "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "MarketWatch":       "https://feeds.marketwatch.com/marketwatch/topstories",
    "Yahoo Finance":     "https://finance.yahoo.com/rss/",
    "CNBC Macro":        "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    "CoinDesk":          "https://coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph":     "https://cointelegraph.com/rss",
    "Decrypt":           "https://decrypt.co/feed",
    "BBC World":         "https://feeds.bbci.co.uk/news/world/rss.xml",
    "NYT World":         "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "NYT Tech":          "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "TechCrunch":        "https://techcrunch.com/feed/",
    "The Verge":         "https://www.theverge.com/rss/index.xml",
    "ESPN":              "https://www.espn.com/espn/rss/news",
    "Yahoo Sports":      "https://sports.yahoo.com/rss/",
    "WSJ Opinion":       "https://feeds.content.dowjones.io/public/rss/RSSOpinion",
    "WSJ World":         "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
    "WSJ US Business":   "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",
    "WSJ Markets":       "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
    "WSJ Tech":          "https://feeds.content.dowjones.io/public/rss/RSSWSJD",
    "WSJ US":            "https://feeds.content.dowjones.io/public/rss/RSSUSnews",
    "WSJ Politics":      "https://feeds.content.dowjones.io/public/rss/socialpoliticsfeed",
    "WSJ Economy":       "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
    "WSJ Sports":        "https://feeds.content.dowjones.io/public/rss/rsssportsfeed",
}

# Maps topic buckets to trigger keywords.
# A headline matching a bucket is only compared to markets in that same bucket.
TOPIC_KEYWORDS = {
    "politics":    ["president", "congress", "senate", "election", "vote", "trump", "biden",
                    "harris", "democrat", "republican", "house", "white house", "governor",
                    "legislation", "impeach", "cabinet", "veto", "executive", "administration",
                    "polling", "approval", "campaign", "party", "nominee"],
    "economy":     ["fed", "federal reserve", "rate", "inflation", "cpi", "gdp", "jobs",
                    "unemployment", "recession", "fomc", "treasury", "debt", "tariff",
                    "fiscal", "deficit", "spending", "budget", "economic", "economy"],
    "crypto":      ["bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "defi",
                    "coinbase", "binance", "stablecoin", "solana", "xrp", "altcoin"],
    "markets":     ["s&p", "nasdaq", "dow", "stock", "equity", "oil", "crude", "gold",
                    "bond", "yield", "ipo", "earnings", "10-year", "market", "index",
                    "futures", "rally", "selloff"],
    "geopolitics": ["ukraine", "russia", "china", "taiwan", "israel", "iran", "nato",
                    "war", "sanction", "missile", "nuclear", "ceasefire", "invasion",
                    "military", "troops", "conflict", "peace", "treaty"],
    "sports":      ["nfl", "nba", "mlb", "nhl", "super bowl", "playoffs", "championship",
                    "fifa", "world cup", "oscar", "grammy", "emmy", "game", "season",
                    "tournament", "draft"],
    "tech":        ["ai", "openai", "google", "apple", "meta", "microsoft", "nvidia",
                    "antitrust", "regulation", "elon musk", "spacex", "tesla", "chatgpt",
                    "model", "chip", "semiconductor"],
}

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "will", "be", "to", "of", "in",
    "on", "at", "by", "for", "with", "from", "that", "this", "it", "as", "its",
    "has", "have", "had", "not", "but", "and", "or", "does", "do", "did", "can",
    "could", "would", "should", "what", "when", "how", "who", "why", "which",
    "says", "said", "new", "more", "after", "over", "than", "also", "into",
    "its", "about", "up", "out", "just", "first", "may", "according"
}

# High-signal proper nouns / entities — these are weighted extra heavily in matching
ENTITY_TERMS = [
    # People
    "trump", "biden", "harris", "obama", "powell", "yellen", "zelensky", "putin",
    "netanyahu", "xi", "modi", "macron", "musk", "altman", "zuckerberg", "cook",
    # Orgs / places
    "fed", "fomc", "nato", "un", "sec", "fbi", "cia", "doj", "supreme court",
    "ukraine", "russia", "china", "taiwan", "israel", "iran", "north korea",
    "bitcoin", "ethereum", "openai", "nvidia", "spacex", "tesla",
    # Numbers and % — extracted dynamically
]


# ── TEXT UTILS ────────────────────────────────────────────────────────────────

def clean_html(text: str) -> str:
    if not text: return ""
    return " ".join(re.sub(r'<.*?>', '', text).split())

def normalize(text: str) -> str:
    """Lowercase, strip punctuation, remove stopwords."""
    text = re.sub(r'[^\w\s%\.\-]', ' ', text.lower())
    tokens = [w for w in text.split() if w not in STOPWORDS and len(w) > 2]
    return " ".join(tokens)

def extract_entities(text: str) -> list[str]:
    """
    Pull high-signal tokens: known entities + any numbers/percentages.
    These are the words that should appear in both headline AND market title
    if they're genuinely about the same event.
    """
    lower = text.lower()
    found = []

    # Known entity terms
    for ent in ENTITY_TERMS:
        if ent in lower:
            found.append(ent)

    # Numbers and percentages (e.g. "5%", "2.5", "100k", "$80")
    numbers = re.findall(r'\b\d+(?:\.\d+)?(?:%|k|b|m)?\b', lower)
    found.extend(numbers)

    return list(set(found))

def get_topics(text: str) -> set:
    lower = text.lower()
    matched = {t for t, kws in TOPIC_KEYWORDS.items() if any(kw in lower for kw in kws)}
    return matched if matched else {"general"}

def build_search_blob(market: dict) -> str:
    """
    Combine all useful market fields into one normalized string.
    We also append entity terms multiple times to upweight them in fuzzy scoring.
    """
    raw = (
        f"{market.get('title', '')} "
        f"{market.get('subtitle', '')} "
        f"{market.get('event_ticker', '')} "
        f"{market.get('category', '')} "
        f"{market.get('yes_sub_title', '')} "
        f"{market.get('no_sub_title', '')}"
    )
    normalized = normalize(clean_html(raw))

    # Repeat entity terms so they score higher in token overlap
    entities = extract_entities(raw)
    boosted  = normalized + " " + " ".join(entities * 2)

    return boosted


# ── KALSHI SYNC ───────────────────────────────────────────────────────────────

def fetch_kalshi_markets() -> list[dict]:
    """Single call for top MARKET_LIMIT open markets. Fast, no pagination needed."""
    print(f"🔄 Fetching top {MARKET_LIMIT} Kalshi markets...")
    try:
        resp = requests.get(
            KALSHI_API_BASE + f"/markets?status=open&limit={MARKET_LIMIT}",
            timeout=15
        )
        resp.raise_for_status()
        markets = resp.json().get("markets", [])
    except Exception as e:
        print(f"⚠️  Kalshi API failed: {e}")
        return []

    catalog = []
    for m in markets:
        blob = build_search_blob(m)
        catalog.append({
            "ticker":      m["ticker"],
            "full_title":  m.get("title", ""),
            "search_text": blob,
            "topics":      get_topics(blob),
            "entities":    set(extract_entities(blob)),
        })

    print(f"✅ Loaded {len(catalog)} markets.")
    return catalog

def build_topic_index(catalog: list[dict]) -> dict:
    index = {}
    for item in catalog:
        for topic in item["topics"]:
            index.setdefault(topic, []).append(item)
    return index


# ── MATCHING ──────────────────────────────────────────────────────────────────

def find_best_match(
    headline: str,
    topic_index: dict,
    catalog: list[dict]
) -> tuple[str | None, float]:

    if not catalog:
        return None, 0

    normalized_hl   = normalize(headline)
    headline_topics = get_topics(headline)
    headline_entities = set(extract_entities(headline))

    # ── Stage 1: topic pre-filter ──
    candidate_set = set()
    candidates    = []
    for topic in headline_topics:
        for item in topic_index.get(topic, []):
            if item["ticker"] not in candidate_set:
                candidate_set.add(item["ticker"])
                candidates.append(item)
    for item in topic_index.get("general", []):
        if item["ticker"] not in candidate_set:
            candidate_set.add(item["ticker"])
            candidates.append(item)

    if len(candidates) < 20:
        candidates = catalog   # fallback to full list

    # ── Stage 2: entity pre-filter (if headline has known entities) ──
    # Prioritise markets that share at least one entity with the headline
    if headline_entities:
        entity_matches = [c for c in candidates if c["entities"] & headline_entities]
        if len(entity_matches) >= 5:
            candidates = entity_matches   # tighter pool, much higher precision

    search_texts = [c["search_text"] for c in candidates]

    # ── Stage 3: multi-metric fuzzy scoring ──
    match_tsr  = process.extractOne(normalized_hl, search_texts, scorer=fuzz.token_set_ratio)
    match_pr   = process.extractOne(normalized_hl, search_texts, scorer=fuzz.partial_ratio)
    match_tsort = process.extractOne(normalized_hl, search_texts, scorer=fuzz.token_sort_ratio)

    scores: dict[str, float] = {}   # ticker → best weighted score

    for match, weight in [(match_tsr, 0.5), (match_pr, 0.3), (match_tsort, 0.2)]:
        if not match:
            continue
        _, score, idx = match
        ticker = candidates[idx]["ticker"]
        scores[ticker] = scores.get(ticker, 0) + score * weight

    if not scores:
        return None, 0

    best_ticker = max(scores, key=lambda t: scores[t])
    # Normalise back to 0–100
    total_weight = (0.5 if match_tsr else 0) + (0.3 if match_pr else 0) + (0.2 if match_tsort else 0)
    final_score  = scores[best_ticker] / total_weight if total_weight else 0

    # ── Entity bonus: reward shared proper nouns ──
    best_market  = next(c for c in candidates if c["ticker"] == best_ticker)
    shared_ents  = headline_entities & best_market["entities"]
    entity_bonus = min(len(shared_ents) * 3, 10)   # up to +10 points
    final_score  = min(final_score + entity_bonus, 100)

    if final_score >= MATCH_THRESHOLD:
        return best_ticker, round(final_score, 2)

    return None, 0


# ── STATE ─────────────────────────────────────────────────────────────────────

def get_processed_links() -> set:
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'link' in df.columns:
                return set(df['link'].astype(str).tolist())
        except Exception as e:
            print(f"Error loading CSV state: {e}")
    return set()


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────

def run_loop():
    seen_links  = get_processed_links()
    catalog     = fetch_kalshi_markets()
    topic_index = build_topic_index(catalog)
    last_sync   = time.time()

    print(f"🚀 Monitoring {len(NEWS_FEEDS)} feeds | "
          f"{len(catalog)} markets | "
          f"{len(seen_links)} links already seen\n")

    while True:
        # Refresh catalog every 15 min
        if time.time() - last_sync > 900:
            catalog     = fetch_kalshi_markets()
            topic_index = build_topic_index(catalog)
            last_sync   = time.time()

        new_entries = []
        now    = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=2)

        for source, url in NEWS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
            except Exception as e:
                print(f"⚠️  Feed error [{source}]: {e}")
                continue

            for entry in feed.entries:
                link = getattr(entry, 'link', None)
                if not link or link in seen_links:
                    continue

                try:
                    raw_date = entry.get('published', entry.get('updated', None))
                    if not raw_date:
                        continue
                    dt = pd.to_datetime(raw_date, utc=True)
                    if dt < cutoff:
                        continue

                    ticker, confidence = find_best_match(entry.title, topic_index, catalog)

                    body_raw   = entry.content[0].value if 'content' in entry else entry.get('summary', '')
                    body_clean = clean_html(body_raw)[:500]

                    new_entries.append({
                        "source":           source,
                        "headline":         entry.title,
                        "matched_ticker":   ticker,
                        "match_confidence": confidence,
                        "content_header":   body_clean,
                        "date":             dt.strftime('%Y-%m-%d %H:%M:%S'),
                        "timestamp":        int(dt.timestamp()),
                        "link":             link,
                    })
                    seen_links.add(link)

                except Exception:
                    continue

        if new_entries:
            new_df      = pd.DataFrame(new_entries)
            file_exists = os.path.isfile(CSV_FILE)
            new_df.to_csv(CSV_FILE, mode='a', index=False, header=not file_exists)

            matches = new_df[new_df['matched_ticker'].notna()]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"New: {len(new_df)} | Matched: {len(matches)}")

            if not matches.empty:
                print(matches[['source', 'headline', 'matched_ticker', 'match_confidence']]
                      .to_string(index=False))
                print()
        else:
            print(".", end="", flush=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        run_loop()
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")