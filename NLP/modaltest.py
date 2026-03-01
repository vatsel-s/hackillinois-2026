import modal

app = modal.App("finnews-sentiment")
image = modal.Image.debian_slim().pip_install("transformers", "torch")


@app.cls(gpu="A10G", image=image, min_containers=1)
class SentimentScorer:
    @modal.enter()
    def load_model(self):
        from transformers import pipeline
        self.pipe = pipeline("text-classification", model="ProsusAI/finbert")

    @modal.method()
    def score(self, text: str) -> dict:
        return self._fmt(self.pipe(text)[0])

    @modal.method()
    def score_batch(self, texts: list[str]) -> list[dict]:
        return [self._fmt(r) for r in self.pipe(texts)]

    def _fmt(self, r: dict) -> dict:
        label = r["label"]
        signal = 1 if label == "positive" else (-1 if label == "negative" else 0)
        return {"label": label, "score": r["score"], "signal": signal}


@app.local_entrypoint()
def main():
    import time
    scorer = SentimentScorer()

    headlines = [
        "Fed raises interest rates by 25 basis points amid inflation concerns",
        "Apple reports record quarterly earnings beating analyst expectations",
        "Oil prices tumble on weak demand outlook from China",
        "Nvidia stock soars after AI chip demand guidance raised",
        "US unemployment rises unexpectedly to 4.2 percent",
    ]

    print(f"Scoring {len(headlines)} headlines...\n")
    start = time.perf_counter()
    results = scorer.score_batch.remote(headlines)
    elapsed = time.perf_counter() - start

    for headline, r in zip(headlines, results):
        signal_str = {1: "POSITIVE", -1: "NEGATIVE", 0: "NEUTRAL"}[r["signal"]]
        print(f"[{signal_str:8s} {r['score']:.3f}]  {headline}")

    print(f"\nDone: {len(headlines)} articles in {elapsed:.2f}s ({elapsed/len(headlines):.3f}s/article)")
