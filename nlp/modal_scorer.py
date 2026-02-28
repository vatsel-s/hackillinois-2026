"""
nlp/modal_scorer.py — Remote FinBERT inference via Modal (serverless GPU).

Usage:
  Set NLP_ARTICLE_MODE=modal in your .env to route article scoring here
  instead of running FinBERT locally.

Deploy:
  modal deploy nlp/modal_scorer.py

The Modal function stays warm across pipeline calls, so cold-start cost
is only paid once. GPU inference is ~5-10x faster than CPU for FinBERT
on long articles.
"""

import modal

# ── Modal app definition ──────────────────────────────────────────────────────
app = modal.App("kalshi-finbert")

_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers>=4.40.0",
        "torch>=2.0.0",
        "accelerate>=0.26.0",
    )
)

# ── Remote inference function ─────────────────────────────────────────────────

@app.function(
    image=_image,
    gpu="T4",
    # Keep one container warm for low-latency repeated calls
    keep_warm=1,
    # Timeout per call (FinBERT on 500 tokens takes ~200ms on T4)
    timeout=30,
)
def finbert_score(text: str) -> tuple[float, str]:
    """
    Run FinBERT sentiment classification on the given text.

    Returns:
        (score, label) where score is in [-1, 1] (negative = bearish,
        positive = bullish) and label is "bullish" | "bearish" | "neutral".
    """
    from transformers import pipeline as hf_pipeline

    # Model is cached in the container image layer after first warm-up
    pipe = hf_pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        tokenizer="ProsusAI/finbert",
        max_length=512,
        truncation=True,
        device=0,  # GPU
    )

    result = pipe(text[:2000])[0]
    label_raw = result["label"].lower()   # "positive" | "negative" | "neutral"
    confidence = result["score"]

    if label_raw == "positive":
        return confidence, "bullish"
    elif label_raw == "negative":
        return -confidence, "bearish"
    else:
        return 0.0, "neutral"


# ── Local entrypoint (for testing the Modal function directly) ────────────────

@app.local_entrypoint()
def main(text: str = "The Federal Reserve raised interest rates by 25 basis points."):
    score, label = finbert_score.remote(text)
    print(f"Score: {score:.4f}  Label: {label}")
