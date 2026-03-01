import pmxt
import json
import os
import torch
from sentence_transformers import SentenceTransformer, util

EMBEDDINGS_FILE = "News/model/market_embeddings.pt"
METADATA_FILE = "News/model/market_metadata.json"

model = SentenceTransformer('all-MiniLM-L6-v2')

def build_and_save_index():
    """Fetch markets, embed them, and save to disk."""
    print("Fetching markets...")
    kalshi = pmxt.Kalshi()
    markets = kalshi.fetch_markets(limit=3000)

    market_data = {}
    for m in markets:
        try:
            outcome_labels = " | ".join(o.label for o in m.outcomes if o.label)
            combined_text = f"{m.title} — {outcome_labels}" if outcome_labels else m.title
            market_data[m.market_id] = {
                "title": m.title,
                "combined_text": combined_text,
                "outcomes": [o.label for o in m.outcomes if o.label]
            }
        except AttributeError:
            pass

    market_ids = list(market_data.keys())
    market_combined_texts = [market_data[mid]["combined_text"] for mid in market_ids]

    print("Embedding markets...")
    market_embeddings = model.encode(market_combined_texts, convert_to_tensor=True)

    # Save embeddings tensor and metadata separately
    torch.save(market_embeddings, EMBEDDINGS_FILE)
    with open(METADATA_FILE, "w") as f:
        json.dump({"market_ids": market_ids, "market_data": market_data}, f)

    print(f"Saved {len(market_ids)} markets to disk.")
    return market_ids, market_data, market_embeddings

def load_index():
    """Load pre-computed embeddings and metadata from disk."""
    print("Loading index from disk...")
    market_embeddings = torch.load(EMBEDDINGS_FILE)
    with open(METADATA_FILE, "r") as f:
        meta = json.load(f)
    return meta["market_ids"], meta["market_data"], market_embeddings

def find_best_market_for_headline(headline: str, market_ids, market_data, market_embeddings, top_k: int = 3):
    headline_embedding = model.encode(headline, convert_to_tensor=True)
    cos_scores = util.cos_sim(headline_embedding, market_embeddings)[0]
    top_results = torch.topk(cos_scores, k=top_k)

    print(f"\nHeadline: '{headline}'")
    for score, idx in zip(top_results[0], top_results[1]):
        market_id = market_ids[idx]
        title = market_data[market_id]["title"]
        outcomes = market_data[market_id]["outcomes"]
        print(f"[{score:.4f}] {title} (ID: {market_id})")
        print(f"         Outcomes: {', '.join(outcomes)}")

# --- On first run, or when you want to refresh market data ---
if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
    market_ids, market_data, market_embeddings = build_and_save_index()
else:
    market_ids, market_data, market_embeddings = load_index()

# --- Instant semantic search from here ---
find_best_market_for_headline("Fed chair announces aggressive 50 basis point cut", market_ids, market_data, market_embeddings)
find_best_market_for_headline("OpenAI releases new flagship model GPT-5", market_ids, market_data, market_embeddings)