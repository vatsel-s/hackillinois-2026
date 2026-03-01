import pmxt
import json
import os
import torch
from datetime import datetime, timezone
from sentence_transformers import SentenceTransformer, util

EMBEDDINGS_FILE = "News/model/market_embeddings.pt"
METADATA_FILE = "News/model/market_metadata.json"

model = SentenceTransformer('all-MiniLM-L6-v2')

def is_open(m):
    status = getattr(m, 'status', None)
    if status is not None:
        return str(status).lower() == 'open'
    resolution_date = getattr(m, 'resolution_date', None)
    if resolution_date is not None:
        return resolution_date > datetime.now(timezone.utc)
    return True

def build_and_save_index():
    print("Fetching open markets...")
    kalshi = pmxt.Kalshi()

    try:
        markets = kalshi.fetch_markets(status='active', limit=2000)
    except TypeError:
        markets = kalshi.fetch_markets(limit=1000)

    open_markets = [m for m in markets if is_open(m)]
    print(f"Found {len(open_markets)} open markets (out of {len(markets)} total)")

    market_data = {}
    for m in open_markets:
        try:
            outcome_labels = " | ".join(o.label for o in m.outcomes if o.label)
            combined_text = f"{m.title} — {outcome_labels}" if outcome_labels else m.title

            # Use dedicated ticker field if available, fall back to market_id
            ticker = getattr(m, 'ticker', None) or m.market_id

            market_data[m.market_id] = {
                "title": m.title,
                "ticker": ticker,
                "combined_text": combined_text,
                "outcomes": [o.label for o in m.outcomes if o.label]
            }
        except AttributeError:
            pass

    market_ids = list(market_data.keys())
    market_combined_texts = [market_data[mid]["combined_text"] for mid in market_ids]

    print(f"Embedding {len(market_ids)} markets...")
    market_embeddings = model.encode(market_combined_texts, convert_to_tensor=True)

    torch.save(market_embeddings, EMBEDDINGS_FILE)
    with open(METADATA_FILE, "w") as f:
        json.dump({"market_ids": market_ids, "market_data": market_data}, f)

    print(f"Saved {len(market_ids)} open markets to disk.")
    return market_ids, market_data, market_embeddings

def load_index():
    print("Loading index from disk...")
    market_embeddings = torch.load(EMBEDDINGS_FILE)
    with open(METADATA_FILE, "r") as f:
        meta = json.load(f)
    return meta["market_ids"], meta["market_data"], market_embeddings

def find_best_market_for_headline(headline, market_ids, market_data, market_embeddings, top_k=3):
    headline_embedding = model.encode(headline, convert_to_tensor=True)
    cos_scores = util.cos_sim(headline_embedding, market_embeddings)[0]
    top_results = torch.topk(cos_scores, k=top_k)

    print(f"\nHeadline: '{headline}'")
    for score, idx in zip(top_results[0], top_results[1]):
        market_id = market_ids[idx]
        info = market_data[market_id]
        outcomes = info.get('outcomes', [])  # safe fallback if key missing
        print(f"[{score:.4f}] {info['title']}")
        print(f"         Ticker:   {market_id}")
        print(f"         Outcomes: {', '.join(outcomes) if outcomes else 'N/A'}")

# --- Load from cache or rebuild ---
if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
    market_ids, market_data, market_embeddings = build_and_save_index()
else:
    market_ids, market_data, market_embeddings = load_index()

# --- Instant semantic search ---
find_best_market_for_headline("Fed chair announces aggressive 50 basis point cut", market_ids, market_data, market_embeddings)
find_best_market_for_headline("OpenAI releases new flagship model GPT-5", market_ids, market_data, market_embeddings)
