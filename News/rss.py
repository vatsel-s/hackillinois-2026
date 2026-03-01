import feedparser
import pandas as pd
import time
import os
import re
from datetime import datetime, timedelta
from dateutil import parser as dateutil_parser
import pytz

EST = pytz.timezone("America/New_York")

CSV_FILE_PATH = "input.csv"

# Filtered Source List (Reuters and AP removed)
NEWS_FEEDS = {
    # General / Home
    "BBC Home": "https://feeds.bbci.co.uk/news/rss.xml",
    "NYT Home": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "The Hill": "https://thehill.com/rss/syndicator/19110",
    
    # Politics / Government
    "NYT Politics": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    "The Hill Politics": "https://thehill.com/homenews/feed",
    "Politico": "https://www.politico.com/rss/politicopicks.xml",
    "WashPost Politics": "https://feeds.washingtonpost.com/rss/politics",
    
    # Economics / Finance / Markets
    "CNBC Business": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories",
    "Yahoo Finance": "https://finance.yahoo.com/rss/",
    
    # Fed / Macro
    "CNBC Macro": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    
    # Crypto
    "CoinDesk": "https://coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    
    # International / Geopolitical
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    
    # Science / Tech / AI
    "NYT Tech": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    
    # Sports
    "ESPN": "https://www.espn.com/espn/rss/news",
    "Yahoo Sports": "https://sports.yahoo.com/rss/",

    #WSJ
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

STATE_FILE = "seen_links.txt"

def load_seen_links():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()

def save_new_link(link):
    with open(STATE_FILE, "a") as f:
        f.write(link + "\n")

def clean_html(text):
    return re.sub(r'<.*?>', '', text) if text else ""

def poll_news(seen_links):
    new_articles = []
    now = datetime.now(EST)
    cutoff = now - timedelta(days=2)

    for source_name, url in NEWS_FEEDS.items():
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            link = getattr(entry, 'link', None)
            if not link or link in seen_links:
                continue
                
            raw_date = entry.get('pubDate', entry.get('updated', None))
            if not raw_date: continue
                
            try:
                dt_obj = dateutil_parser.parse(raw_date).astimezone(EST)
                
                if dt_obj >= cutoff:
                    # Logic to find the best content/summary snippet
                    content_raw = entry.content[0].value if 'content' in entry else entry.get('summary', '')
                    content_clean = clean_html(content_raw)

                    new_articles.append({
                        "timestamp": int(dt_obj.timestamp()),
                        "title": entry.title,
                        "content": content_clean[:500].strip(),
                    })
                    
                    seen_links.add(link)
                    save_new_link(link)

            except Exception:
                continue

    if new_articles:
        df_updates = pd.DataFrame(new_articles).sort_values(by='timestamp', ascending=False).reset_index(drop=True)
        # REMOVE the to_csv line here if you want the Unified Runner to handle the writing
        return df_updates 
    
    return pd.DataFrame()

if __name__ == "__main__":
    print("🚀 Initializing Kalshi-Ready News Pipeline...")
    current_seen = load_seen_links()
    
    while True:
        df_updates = poll_news(current_seen)
        
        if not df_updates.empty:
            print(f"\n🔔 {len(df_updates)} New Events Detected:")
            print(df_updates[['source', 'headline', 'timestamp']].head(10).to_string(index=False))
            df_updates.to_csv("news_updates.csv", mode='a', header=False, index=False)
            # TODO: Your Modal logic here
            # response = modal_function.remote(df_updates.to_dict('records'))
        else:
            # Simple heartbeat for console
            print(".", end="", flush=True)
            
        time.sleep(10) 