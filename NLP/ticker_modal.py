import modal

app = modal.App("finnews-ticker")

volume = modal.Volume.from_name("market-index", create_if_missing=True)
VOLUME_PATH = "/market_index"

image = (
    modal.Image.debian_slim()
    .pip_install("sentence-transformers", "torch", "numpy")
)


@app.cls(gpu="T4", image=image, volumes={VOLUME_PATH: volume}, min_containers=1)
class TickerMatcher:
    @modal.enter()
    def load(self):
        import torch
        import json
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.market_embeddings = torch.load(
            f"{VOLUME_PATH}/market_embeddings.pt", map_location="cuda"
        )
        with open(f"{VOLUME_PATH}/market_metadata.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.market_ids = meta["market_ids"]
        self.market_data = meta["market_data"]

    @modal.method()
    def match_batch(self, titles: list[str]) -> list[dict]:
        import torch
        from sentence_transformers import util

        headline_embeddings = self.model.encode(titles, convert_to_tensor=True)
        cos_sims = util.cos_sim(headline_embeddings, self.market_embeddings)
        best_matches = torch.max(cos_sims, dim=1)

        results = []
        for i, idx in enumerate(best_matches.indices.tolist()):
            m_id = self.market_ids[idx]
            results.append({
                "ticker": self.market_data[m_id]["ticker"],
                "market_title": self.market_data[m_id]["title"],
                "confidence": round(best_matches.values.tolist()[i], 4),
            })
        return results


# --- LOCAL HELPER ---

_matcher = None


def _get_matcher():
    global _matcher
    if _matcher is None:
        Cls = modal.Cls.from_name("finnews-ticker", "TickerMatcher")
        _matcher = Cls()
    return _matcher


def match_tickers(titles: list[str]) -> list[dict]:
    """Batch-match headlines to Kalshi tickers via Modal GPU. Returns list of {ticker, market_title, confidence}."""
    return _get_matcher().match_batch.remote(titles)


# --- ONE-TIME SETUP ---

@app.local_entrypoint()
def upload_index():
    """Run once to upload local market index files to the Modal volume:
        modal run NLP/ticker_modal.py::upload_index
    """
    with volume.batch_upload() as batch:
        batch.put_file("News/model/market_embeddings.pt", "/market_embeddings.pt")
        batch.put_file("News/model/market_metadata.json", "/market_metadata.json")
    print("Market index uploaded to Modal volume 'market-index'.")
