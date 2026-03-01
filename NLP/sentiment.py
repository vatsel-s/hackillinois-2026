import modal
import csv
import os
from datetime import datetime

CSV_PATH = "sentiment_output.csv"
CSV_COLUMNS = ["timestamp", "source", "headline", "content_header", "link", "ticker", "confidence", "label", "score", "signal"]

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


def score_and_write(articles: list[dict]) -> list[dict]:
    """
    Score a batch of articles and append results to sentiment_output.csv.

    Each article dict should have keys: source, headline, content_header, timestamp, link
    (matches the output of News/rss.py poll_news).

    Returns the enriched list of dicts with label/score/signal added.
    """
    if not articles:
        return []

    texts = [a["headline"] for a in articles]
    scores = score_headlines(texts)

    write_header = not os.path.exists(CSV_PATH)
    enriched = []
    with open(CSV_PATH, "a", newline="", encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        for article, s in zip(articles, scores):
            row = {
                "timestamp": article.get("timestamp", int(datetime.utcnow().timestamp())),
                "source": article.get("source", ""),
                "headline": article.get("headline", ""),
                "content_header": article.get("content_header", ""),
                "link": article.get("link", ""),
                "ticker": article.get("ticker", "N/A"),       # Preserves ticker
                "confidence": article.get("confidence", 0.0), # Preserves confidence
                **s,
            }
            writer.writerow(row)
            enriched.append(row)

    return enriched
