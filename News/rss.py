import asyncio
import aiohttp
import feedparser
import pandas as pd
import os
import re
import json
import torch
import pmxt
from datetime import datetime, timedelta, timezone
from sentence_transformers import SentenceTransformer, util
import time

# --- CONFIGURATION ---
CSV_FILE = "news_log.csv"
POLL_INTERVAL = 10  # Reduced to 10s because Async is efficient
USER_AGENT = "Mozilla/5.0 (compatible; HackIllinoisBot/1.0)"

# AI Model Config
EMBEDDINGS_FILE = "News/model/market_embeddings.pt"
METADATA_FILE = "News/model/market_metadata.json"
MODEL_NAME = 'all-MiniLM-L6-v2' 

# Aggregated Source List
NEWS_FEEDS = {
    "NYT Home": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "The Hill": "https://thehill.com/rss/syndicator/19110",
    "NYT Politics": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    "The Hill Politics": "https://thehill.com/homenews/feed",
    "Politico": "https://www.politico.com/rss/politicopicks.xml",
    "WashPost Politics": "https://feeds.washingtonpost.com/rss/politics",
    "CNBC Business": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories",
    "Yahoo Finance": "https://finance.yahoo.com/rss/",
    "CNBC Macro": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    "CoinDesk": "https://coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "NYT Tech": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "ESPN": "https://www.espn.com/espn/rss/news",
    "Yahoo Sports": "https://sports.yahoo.com/rss/",
    "WSJ Opinion": "https://feeds.content.dowjones.io/public/rss/RSSOpinion", 
    "WSJ WORLD": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews", 
    "WSJ US BUSINESS": "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness", 
    "WSJ MARKETS": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", 
    "WSJ TECH": "https://feeds.content.dowjones.io/public/rss/RSSWSJD", 
    "WSJ US": "https://feeds.content.dowjones.io/public/rss/RSSUSnews", 
    "WSJ POLITICS": "https://feeds.content.dowjones.io/public/rss/socialpoliticsfeed", 
    "WSJ ECONOMY": "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
    "WSJ SPORTS": "https://feeds.content.dowjones.io/public/rss/rsssportsfeed"
}

# --- GLOBAL MODEL INIT ---
print("🤖 Initializing Sentence Transformer...")
model = SentenceTransformer(MODEL_NAME)

# --- MARKET INDEXING (Same as before) ---

def ensure_directory(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def is_open(m):
    """Checks if a market is active."""
    status = getattr(m, 'status', None)
    if status and str(status).lower() == 'active': return True
    # Fallback logic for dates omitted for brevity, keeping it fast
    return True

def load_or_build_index():
    """Loads index if exists, otherwise builds it."""
    if os.path.exists(EMBEDDINGS_FILE) and os.path.exists(METADATA_FILE):
        try:
            print("📂 Loading index from disk...")
            embeddings = torch.load(EMBEDDINGS_FILE)
            with open(METADATA_FILE, "r") as f:
                meta = json.load(f)
            return meta["market_ids"], meta["market_data"], embeddings
        except:
            pass
    
    # Build Index
    print("📉 Fetching active markets from Kalshi...")
    try:
        kalshi = pmxt.Kalshi()
        markets = kalshi.fetch_markets(status='active', limit=3000)
    except:
        return [], {}, None

    valid_ids, market_data, combined_texts = [], {}, []
    
    for m in markets:
        if not is_open(m): continue
        try:
            outcome_labels = " | ".join(o.label for o in m.outcomes if o.label)
            combined_text = f"{m.title} — {outcome_labels}" if outcome_labels else m.title
            ticker = getattr(m, 'ticker', None) or m.market_id
            
            market_data[m.market_id] = {
                "title": m.title, "ticker": str(ticker)[:15], "combined_text": combined_text
            }
            valid_ids.append(m.market_id)
            combined_texts.append(combined_text)
        except: continue

    print(f"🧠 Embedding {len(valid_ids)} markets...")
    embeddings = model.encode(combined_texts, convert_to_tensor=True)
    
    ensure_directory(EMBEDDINGS_FILE)
    torch.save(embeddings, EMBEDDINGS_FILE)
    with open(METADATA_FILE, "w") as f:
        json.dump({"market_ids": valid_ids, "market_data": market_data}, f)
        
    return valid_ids, market_data, embeddings

def get_market_matches(headline, market_ids, market_data, market_embeddings, top_k=3):
    if market_embeddings is None: return []
    headline_emb = model.encode(headline, convert_to_tensor=True)
    cos_scores = util.cos_sim(headline_emb, market_embeddings)[0]
    top_results = torch.topk(cos_scores, k=top_k)
    
    matches = []
    for score, idx in zip(top_results[0], top_results[1]):
        m_id = market_ids[idx]
        matches.append({
            "ticker": market_data[m_id]['ticker'],
            "score": float(score)
        })
    return matches

# --- ASYNC RSS ENGINE ---

def clean_text(text):
    if not text: return ""
    return " ".join(re.sub(r'<.*?>', '', text).split()).strip()

def get_processed_links():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if 'link' in df.columns: return set(df['link'].astype(str).tolist())
        except: pass
    return set()

async def fetch_feed(session, source_name, url, seen_links, cutoff, market_ids, market_data, market_embeddings):
    """
    Async function to fetch a single feed and process its articles immediately.
    """
    new_items = []
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200: return []
            xml_data = await response.text()
            
            # Feedparser is blocking, but it's fast on local string data
            feed = feedparser.parse(xml_data)
            
            for entry in feed.entries:
                link = getattr(entry, 'link', None)
                if not link or link in seen_links: continue
                
                # Basic date check
                dt = datetime.now(timezone.utc) # Default to now if parsing fails
                if 'published' in entry:
                    try: dt = pd.to_datetime(entry.published, utc=True)
                    except: pass
                
                if dt < cutoff: continue
                
                headline = clean_text(entry.title)
                
                # --- MATCHING HAPPENS HERE ---
                matches = get_market_matches(headline, market_ids, market_data, market_embeddings)
                
                new_items.append({
                    "source": source_name,
                    "headline": headline,
                    "date": dt.strftime('%Y-%m-%d %H:%M:%S'),
                    "link": link,
                    "Match_1_Ticker": matches[0]['ticker'] if len(matches) > 0 else None,
                    "Match_1_Score": round(matches[0]['score'], 4) if len(matches) > 0 else None,
                    "Match_2_Ticker": matches[1]['ticker'] if len(matches) > 1 else None,
                    "Match_2_Score": round(matches[1]['score'], 4) if len(matches) > 1 else None
                })
                seen_links.add(link)
                
    except Exception as e:
        # Silently fail on individual feed errors to keep the stream moving
        pass
        
    return new_items

async def main_loop():
    # 1. Load Data
    market_ids, market_data, market_embeddings = load_or_build_index()
    seen_links = get_processed_links()
    
    print(f"🚀 ASYNC STREAM STARTED: Monitoring {len(NEWS_FEEDS)} feeds.")

    async with aiohttp.ClientSession(headers={'User-Agent': USER_AGENT}) as session:
        while True:
            start_time = time.time()
            cutoff = datetime.now(timezone.utc) - timedelta(days=2)
            
            # 2. Create tasks for ALL feeds to run at the SAME time
            tasks = []
            for source, url in NEWS_FEEDS.items():
                task = fetch_feed(session, source, url, seen_links, cutoff, market_ids, market_data, market_embeddings)
                tasks.append(task)
            
            # 3. Wait for all to finish (Parallel execution)
            results = await asyncio.gather(*tasks)
            
            # 4. Flatten results
            flat_articles = [item for sublist in results for item in sublist]
            
            if flat_articles:
                new_df = pd.DataFrame(flat_articles)
                file_exists = os.path.isfile(CSV_FILE)
                new_df.to_csv(CSV_FILE, mode='a', index=False, header=not file_exists)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ Processed {len(flat_articles)} new headlines.")
                print(new_df[['source', 'headline', 'Match_1_Ticker', 'Match_1_Score']].head(3).to_string(index=False))
            else:
                print(".", end="", flush=True)
            
            # Smart Sleep: Adjust sleep based on how long the fetch took
            elapsed = time.time() - start_time
            sleep_time = max(1, POLL_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    # Windows Selector Policy fix (if needed for Python 3.8+)
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main_loop())