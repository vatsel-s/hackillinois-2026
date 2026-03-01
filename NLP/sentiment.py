import modal
import csv
import os
from datetime import datetime

CSV_PATH = "sentiment_output.csv"
CSV_COLUMNS = [
    "timestamp", "source", "headline", "content_header", "link",
    "ticker", "market_title", "ticker_confidence",
    "finbert_label", "finbert_score", "finbert_signal",
    "llm_signal", "llm_source", "llm_reasoning",
    "final_signal", "final_decision",
]

_scorer = None


def _get_scorer():
    global _scorer
    if _scorer is None:
        Cls = modal.Cls.from_name("finnews-sentiment", "SentimentScorer")
        _scorer = Cls()
    return _scorer


def score_headline(text: str) -> dict:
    """Score a single headline. Returns {'label', 'score', 'signal'}."""
    return _get_scorer().score.remote(text)


def score_headlines(texts: list[str]) -> list[dict]:
    """Batch score headlines in a single GPU call. Returns list of {'label', 'score', 'signal'}."""
    return _get_scorer().score_batch.remote(texts)


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Score a batch of articles with FinBERT. No CSV write — returns enriched dicts.

    Each article dict should have keys: source, headline, content_header, timestamp,
    link, ticker, market_title, confidence (from ticker matching).

    Returns enriched list with finbert_label/finbert_score/finbert_signal added.
    """
    if not articles:
        return []

    texts = [a["headline"] for a in articles]
    scores = score_headlines(texts)

    enriched = []
    for article, s in zip(articles, scores):
        enriched.append({
            "timestamp":         article.get("timestamp", int(datetime.utcnow().timestamp())),
            "source":            article.get("source", ""),
            "headline":          article.get("headline", ""),
            "content_header":    article.get("content_header", ""),
            "link":              article.get("link", ""),
            "ticker":            article.get("ticker", "N/A"),
            "market_title":      article.get("market_title", ""),
            "ticker_confidence": article.get("confidence", 0.0),
            "finbert_label":     s["label"],
            "finbert_score":     s["score"],
            "finbert_signal":    s["signal"],
        })

    return enriched


def write_decisions(rows: list[dict]):
    """
    Append complete decision rows (all 16 fields) to sentiment_output.csv.
    Called after resolve_signal so LLM fields are available.
    """
    if not rows:
        return
    write_header = not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
