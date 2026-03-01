import feedparser
import pandas as pd
import time
import os
import re
import json
import torch
import pmxt
from datetime import datetime, timedelta, timezone
from sentence_transformers import SentenceTransformer, util

# --- CONFIGURATION ---
CSV_FILE = "news_log.csv"
POLL_INTERVAL = 30  # Interval to check feeds in seconds

# AI Model Configuration
EMBEDDINGS_FILE = "News/model/market_embeddings.pt"
METADATA_FILE = "News/model/market_metadata.json"
MODEL_NAME = 'all-MiniLM-L6-v2' 

# Aggregated Source List
NEWS_FEEDS = {
    "NYT Home": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    # "NPR": "https://feeds.npr.org/1001/rss.xml",
    # "The Hill": "https://thehill.com/rss/syndicator/19110",
    # "NYT Politics": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    # "The Hill Politics": "https://thehill.com/homenews/feed",
    # "Politico": "https://www.politico.com/rss/politicopicks.xml",
    # "WashPost Politics": "https://feeds.washingtonpost.com/rss/politics",
    # "CNBC Business": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    # "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories",
    # "Yahoo Finance": "https://finance.yahoo.com/rss/",
    # "CNBC Macro": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    # "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    # "CoinDesk": "https://coindesk.com/arc/outboundfeeds/rss/",
    # "CoinTelegraph": "https://cointelegraph.com/rss",
    # "Decrypt": "https://decrypt.co/feed",
    # "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    # "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    # "NYT Tech": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    # "TechCrunch": "https://techcrunch.com/feed/",
    # "The Verge": "https://www.theverge.com/rss/index.xml",
    # "ESPN": "https://www.espn.com/espn/rss/news",
    # "Yahoo Sports": "https://sports.yahoo.com/rss/",
    # "WSJ Opinion": "https://feeds.content.dowjones.io/public/rss/RSSOpinion", 
    # "WSJ WORLD": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews", 
    # "WSJ US BUSINESS": "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness", 
    # "WSJ MARKETS": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", 
    # "WSJ TECH": "https://feeds.content.dowjones.io/public/rss/RSSWSJD", 
    # "WSJ US": "https://feeds.content.dowjones.io/public/rss/RSSUSnews", 
    # "WSJ POLITICS": "https://feeds.content.dowjones.io/public/rss/socialpoliticsfeed", 
    # "WSJ ECONOMY": "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
    # "WSJ SPORTS": "https://feeds.content.dowjones.io/public/rss/rsssportsfeed"
}

# --- GLOBAL MODEL INIT ---
print("🤖 Initializing Sentence Transformer...")
model = SentenceTransformer(MODEL_NAME)

# --- HELPER FUNCTIONS ---

def ensure_directory(file_path):
    """Creates the directory if it doesn't exist to prevent save errors."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created directory: {directory}")

def is_open(m):
    """Checks if a market is currently active/open."""
    status = getattr(m, 'status', None)
    if status is not None:
        return str(status).lower() == 'active' # API usually returns 'active', checking safety
    
    # Fallback to date check
    resolution_date = getattr(m, 'resolution_date', None)
    if resolution_date is not None:
        # PMXT often returns datetime objects, but if string, we might need parsing. 
        # Assuming datetime object here based on your snippet.
        if isinstance(resolution_date, str):
            try:
                resolution_date = pd.to_datetime(resolution_date).to_pydatetime()
            except:
                pass
        if isinstance(resolution_date, datetime):
            # Ensure timezone awareness for comparison
            if resolution_date.tzinfo is None:
                resolution_date = resolution_date.replace(tzinfo=timezone.utc)
            return resolution_date > datetime.now(timezone.utc)
    return True

# --- MARKET INDEXING LOGIC (YOUR VERSION) ---

def build_and_save_index():
    print("📉 Fetching open markets from Kalshi...")
    try:
        kalshi = pmxt.Kalshi()
        # Try fetching with status filter first
        try:
            markets = kalshi.fetch_markets(status='active', limit=3000)
        except TypeError:
            markets = kalshi.fetch_markets(limit=3000)
    except Exception as e:
        print(f"❌ API Error: {e}")
        return [], {}, None

    # Filter for Open Markets
    open_markets = [m for m in markets if is_open(m)]
    print(f"✅ Found {len(open_markets)} open markets (out of {len(markets)} total)")

    market_data = {}
    market_combined_texts = []
    valid_ids = []

    for m in open_markets:
        try:
            outcome_labels = " | ".join(o.label for o in m.outcomes if o.label)
            combined_text = f"{m.title} — {outcome_labels}" if outcome_labels else m.title

            # Use dedicated ticker field if available, fall back to market_id
            ticker = getattr(m, 'ticker', None) or m.market_id
            # Clean ticker if it's the long ID (take first 8 chars for display if it looks like a hash)
            display_ticker = ticker
            if len(str(ticker)) > 20 and "-" not in str(ticker): 
                 display_ticker = str(ticker)[:10] + "..."

            market_data[m.market_id] = {
                "title": m.title,
                "ticker": display_ticker,
                "combined_text": combined_text,
                "outcomes": [o.label for o in m.outcomes if o.label]
            }
            valid_ids.append(m.market_id)
            market_combined_texts.append(combined_text)
        except AttributeError:
            pass

    if not valid_ids:
        print("⚠️ No valid markets found.")
        return [], {}, None

    print(f"🧠 Embedding {len(valid_ids)} markets...")
    market_embeddings = model.encode(market_combined_texts, convert_to_tensor=True)

    # Save
    ensure_directory(EMBEDDINGS_FILE)
    ensure_directory(METADATA_FILE)
    
    torch.save(market_embeddings, EMBEDDINGS_FILE)
    with open(METADATA_FILE, "w") as f:
        json.dump({"market_ids": valid_ids, "market_data": market_data}, f)

    print(f"💾 Saved index to disk.")
    return valid_ids, market_data, market_embeddings

def load_index():
    """Load pre-computed embeddings and metadata from disk."""
    if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
        return build_and_save_index()

    print("📂 Loading index from disk...")
    try:
        market_embeddings = torch.load(EMBEDDINGS_FILE)
        with open(METADATA_FILE, "r") as f:
            meta = json.load(f)
        return meta["market_ids"], meta["market_data"], market_embeddings
    except Exception:
        print("❌ Load failed. Rebuilding...")
        return build_and_save_index()

def get_market_matches(headline, market_ids, market_data, market_embeddings, top_k=3):
    """Return top matches for the RSS Loop."""
    if market_embeddings is None or len(market_ids) == 0:
        return []

    headline_embedding = model.encode(headline, convert_to_tensor=True)
    cos_scores = util.cos_sim(headline_embedding, market_embeddings)[0]
    top_results = torch.topk(cos_scores, k=top_k)

    matches = []
    for score, idx in zip(top_results[0], top_results[1]):
        m_id = market_ids[idx]
        info = market_data[m_id]
        matches.append({
            "ticker": info['ticker'],
            "title": info['title'],
            "score": float(score),
            "id": m_id
        })
    return matches

# --- RSS LOGGING LOOP ---

def get_processed_links():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'link' in df.columns:
                return set(df['link'].astype(str).tolist())
        except Exception:
            pass
    return set()

def clean_text(text):
    if not text: return ""
    text = re.sub(r'<.*?>', '', text)
    return " ".join(text.split()).strip()

def run_loop():
    # 1. Load Data
    market_ids, market_data, market_embeddings = load_index()
    
    seen_links = get_processed_links()
    print(f"🚀 Monitoring {len(NEWS_FEEDS)} feeds + Real-time Semantic Matching.")

    while True:
        pending_articles = []
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(days=2))

        for source, url in NEWS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
            except Exception:
                continue

            for entry in feed.entries:
                link = getattr(entry, 'link', None)
                if not link or link in seen_links:
                    continue
                
                try:
                    raw_date = entry.get('published', entry.get('updated', None))
                    if not raw_date: continue
                    dt = pd.to_datetime(raw_date, utc=True)
                    if dt < cutoff: continue
                    
                    headline = clean_text(entry.title)
                    body_raw = entry.content[0].value if 'content' in entry else entry.get('summary', '')
                    body_clean = clean_text(body_raw)

                    # --- MATCHING LOGIC ---
                    matches = get_market_matches(headline, market_ids, market_data, market_embeddings)
                    
                    article_data = {
                        "source": source,
                        "headline": headline,
                        "content_header": body_clean[:500],
                        "date": dt.strftime('%Y-%m-%d %H:%M:%S'),
                        "timestamp": int(dt.timestamp()),
                        "link": link,
                        
                        # Top 3 Matches
                        "Match_1_Ticker": matches[0]['ticker'] if len(matches) > 0 else None,
                        "Match_1_Score":  round(matches[0]['score'], 4) if len(matches) > 0 else None,
                        
                        "Match_2_Ticker": matches[1]['ticker'] if len(matches) > 1 else None,
                        "Match_2_Score":  round(matches[1]['score'], 4) if len(matches) > 1 else None,
                        
                        "Match_3_Ticker": matches[2]['ticker'] if len(matches) > 2 else None,
                        "Match_3_Score":  round(matches[2]['score'], 4) if len(matches) > 2 else None,
                    }

                    pending_articles.append(article_data)
                    seen_links.add(link)
                except Exception:
                    continue

        if pending_articles:
            new_df = pd.DataFrame(pending_articles)
            file_exists = os.path.isfile(CSV_FILE)
            new_df.to_csv(CSV_FILE, mode='a', index=False, header=not file_exists)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Logged {len(pending_articles)} new articles.")
            print(new_df[['headline', 'Match_1_Ticker', 'Match_1_Score']].head(3).to_string(index=False))
        else:
            print(".", end="", flush=True)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_loop()