import time
import threading
import pandas as pd
import os
import torch
import json
from datetime import datetime, timezone
from sentence_transformers import SentenceTransformer, util

# Import your existing scrapers
from gkg_test import extract_clean_df
from rss import poll_news, load_seen_links

# --- CONFIGURATION ---
CSV_FILE = "input.csv"
GKG_INTERVAL = 15 * 60
RSS_INTERVAL = 10
EMBEDDINGS_FILE = "News/model/market_embeddings.pt"
METADATA_FILE = "News/model/market_metadata.json"

# --- INITIALIZE MODEL ---
print("Loading NLP Model and Market Index...")
model = SentenceTransformer('all-MiniLM-L6-v2')

def load_index():
    if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
        raise FileNotFoundError("Market index files missing. Run build_and_save_index() first.")
    
    market_embeddings = torch.load(EMBEDDINGS_FILE)
    with open(METADATA_FILE, "r", encoding='utf-8') as f:
        meta = json.load(f)
    return meta["market_ids"], meta["market_data"], market_embeddings

# Load globally for threads to access
MARKET_IDS, MARKET_DATA, MARKET_EMBEDDINGS = load_index()

def process_and_append(df: pd.DataFrame):
    """Enriches news with Kalshi tickers and confidence scores before saving."""
    if df.empty:
        return

    print(f"Enriching {len(df)} articles with market tickers...")
    
    titles = df['title'].tolist()
    # Vectorized encoding of the batch
    headline_embeddings = model.encode(titles, convert_to_tensor=True)
    
    # Calculate cosine similarity against all markets
    cos_sims = util.cos_sim(headline_embeddings, MARKET_EMBEDDINGS)
    
    # Find best match for each headline
    best_matches = torch.max(cos_sims, dim=1)
    scores = best_matches.values.tolist()
    indices = best_matches.indices.tolist()

    matched_tickers = []
    matched_titles = []
    confidence_scores = []

    for i, idx in enumerate(indices):
        m_id = MARKET_IDS[idx]
        matched_tickers.append(MARKET_DATA[m_id]['ticker'])
        matched_titles.append(MARKET_DATA[m_id]['title'])
        confidence_scores.append(round(scores[i], 4))

    # Add new columns
    df['ticker'] = matched_tickers
    df['market_title'] = matched_titles
    df['confidence'] = confidence_scores

    # Write to CSV (header only if file doesn't exist)
    file_exists = os.path.isfile(CSV_FILE)
    df.to_csv(CSV_FILE, mode="a", header=not file_exists, index=False, encoding='utf-8')
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