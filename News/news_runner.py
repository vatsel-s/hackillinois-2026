import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import threading
import pandas as pd
from NLP.ticker_modal import match_tickers

# Import your existing scrapers
from gkg_test import extract_clean_df
from rss import poll_news, load_seen_links

# --- CONFIGURATION ---
CSV_FILE = "input.csv"
GKG_INTERVAL = 15 * 60
RSS_INTERVAL = 10


def process_and_append(df: pd.DataFrame):
    """Enriches news with Kalshi tickers and confidence scores before saving."""
    if df.empty:
        return

    print(f"Enriching {len(df)} articles with market tickers (via Modal GPU)...")

    # Normalize column names and fill missing fields
    df = df.rename(columns={"title": "headline", "content": "content_header"})
    if "source" not in df.columns:
        df["source"] = "GDELT"
    if "link" not in df.columns:
        df["link"] = ""

    titles = df['headline'].tolist()
    matches = match_tickers(titles)

    df['ticker'] = [m['ticker'] for m in matches]
    df['market_title'] = [m['market_title'] for m in matches]
    df['confidence'] = [m['confidence'] for m in matches]

    has_content = os.path.isfile(CSV_FILE) and os.path.getsize(CSV_FILE) > 0
    df.to_csv(CSV_FILE, mode="a", header=not has_content, index=False, encoding='utf-8')
    print(f"Successfully appended {len(df)} enriched rows to {CSV_FILE}")

def gkg_loop():
    while True:
        try:
            print("[GKG] Fetching GKG snapshot...")
            raw = extract_clean_df()
            if not raw.empty:
                out = raw.rename(columns={"themes": "content"})
                # We only need: timestamp, title, content
                process_and_append(out)
        except Exception as e:
            print(f"[GKG] Error: {e}")
        time.sleep(GKG_INTERVAL)

def rss_loop(seen_links: set):
    while True:
        try:
            # poll_news must return a DataFrame for this to work
            df_rss = poll_news(seen_links)
            if df_rss is not None and not df_rss.empty:
                process_and_append(df_rss)
        except Exception as e:
            print(f"[RSS] Error: {e}")
        time.sleep(RSS_INTERVAL)

if __name__ == "__main__":
    print("Starting enriched news pipeline...")
    seen = load_seen_links()

    gkg_thread = threading.Thread(target=gkg_loop, daemon=True, name="GKG")
    gkg_thread.start()

    rss_loop(seen)