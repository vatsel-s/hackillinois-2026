import modal

app = modal.App("finnews-sentiment")
image = modal.Image.debian_slim().pip_install("transformers", "torch")


@app.cls(name="SentimentScorer", gpu="A10G", image=image, min_containers=1)
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
