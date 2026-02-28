"""
nlp/scorer.py — Two-stage NLP pipeline for Kalshi signal generation.

STAGE 1 — Headline scoring (fast, ~1ms):
  - Keyword matching against Kalshi market categories
  - VADER sentiment (lexicon-based, no model loading)
  - Optional: FinBERT headline scoring if NLP_HEADLINE_MODE = "finbert"

STAGE 2 — Article scoring (deep, async, ~50–200ms):
  - FinBERT transformer sentiment on full article text
  - Only runs when a headline clears Stage 1 threshold
  - Updates signal_score with a weighted blend

Why this two-stage approach?
  Headlines: 1ms response, sufficient for 90% of signals. Short text →
  VADER is actually competitive with FinBERT on headline-length input.
  Full articles: FinBERT on 300-500 tokens gives significantly better
  sentiment accuracy, especially for nuanced language like Fed minutes,
  earnings reports, or diplomatic statements.
"""

import logging
import re
from typing import Optional

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from config import (
    KALSHI_MARKET_KEYWORDS,
    NLP_HEADLINE_MODE,
    NLP_ARTICLE_MODE,
    NLP_MIN_SIGNAL_SCORE,
)
from utils.models import NewsEvent

logger = logging.getLogger("nlp")

# ── VADER (always loaded — it's just a lexicon, no GPU) ──────────────────────
_vader = SentimentIntensityAnalyzer()

# ── FinBERT (lazy-loaded on first use to avoid startup delay) ────────────────
_finbert_pipeline = None

def _get_finbert():
    global _finbert_pipeline
    if _finbert_pipeline is None:
        try:
            from transformers import pipeline as hf_pipeline
            logger.info("Loading FinBERT model (first use)...")
            _finbert_pipeline = hf_pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
                max_length=512,
                truncation=True,
            )
            logger.info("FinBERT loaded successfully")
        except Exception as e:
            logger.warning(f"FinBERT unavailable ({e}). Falling back to VADER.")
    return _finbert_pipeline


# ── Pre-compiled regex patterns per market ────────────────────────────────────
_market_patterns: dict[str, re.Pattern] = {}

def _build_patterns():
    for market, keywords in KALSHI_MARKET_KEYWORDS.items():
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b",
            re.IGNORECASE,
        )
        _market_patterns[market] = pattern

_build_patterns()


# ── Public API ────────────────────────────────────────────────────────────────

def score_headline(event: NewsEvent) -> NewsEvent:
    """
    Stage 1: Score a headline in ~1ms.
    - Identifies which Kalshi markets this article touches
    - Assigns sentiment score (-1.0 = very bearish, +1.0 = very bullish)
    - Sets signal_score (None if below threshold → don't trade)
    """
    text = event.headline

    # 1. Match Kalshi markets
    matched = []
    for market, pattern in _market_patterns.items():
        if pattern.search(text):
            matched.append(market)
    event.matched_markets = matched

    if not matched:
        # No relevant market match — skip deep NLP
        event.headline_sentiment = 0.0
        event.headline_label = "neutral"
        event.signal_score = None
        return event

    # 2. Sentiment
    if NLP_HEADLINE_MODE == "finbert":
        sentiment, label = _finbert_score(text)
    else:
        sentiment, label = _vader_score(text)

    event.headline_sentiment = sentiment
    event.headline_label = label

    # 3. Compute headline-level signal score
    # Boost by number of matched markets (more relevant → stronger signal)
    market_boost = min(len(matched) * 0.1, 0.3)
    raw_score = abs(sentiment) + market_boost
    event.signal_score = min(raw_score, 1.0)

    return event


async def score_article_async(event: NewsEvent) -> NewsEvent:
    """
    Stage 2: Deep FinBERT scoring on full article text (async).
    Only called when signal_score >= NLP_MIN_SIGNAL_SCORE.
    Blends headline + article sentiment for a final signal_score.

    When NLP_ARTICLE_MODE=modal the scoring runs on a remote Modal GPU;
    otherwise it falls back to local FinBERT (or VADER if unavailable).
    """
    if not event.full_text or len(event.full_text.strip()) < 50:
        return event  # not enough text for deep scoring

    import asyncio
    loop = asyncio.get_event_loop()

    if NLP_ARTICLE_MODE == "modal":
        article_sentiment, _ = await _modal_score_async(event.full_text[:2000])
    else:
        # Run FinBERT in thread pool (it's CPU/GPU-bound, not async-native)
        article_sentiment, _ = await loop.run_in_executor(
            None, _finbert_score, event.full_text[:2000]  # cap at ~500 tokens
        )

    event.article_sentiment = article_sentiment

    # Blend: 40% headline, 60% article (article is more reliable)
    headline_s = event.headline_sentiment or 0.0
    blended = (0.4 * headline_s) + (0.6 * article_sentiment)

    # Recompute signal score with blended sentiment
    market_boost = min(len(event.matched_markets) * 0.1, 0.3)
    event.signal_score = min(abs(blended) + market_boost, 1.0)

    return event


def is_tradeable(event: NewsEvent) -> bool:
    """Return True if this event clears the minimum signal threshold."""
    return (
        event.signal_score is not None
        and event.signal_score >= NLP_MIN_SIGNAL_SCORE
        and len(event.matched_markets) > 0
    )


# ── Internal scorers ──────────────────────────────────────────────────────────

def _vader_score(text: str) -> tuple[float, str]:
    """
    VADER sentiment: designed for social media / short texts.
    compound score is in [-1, 1].
    """
    scores = _vader.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.05:
        label = "bullish"
    elif compound <= -0.05:
        label = "bearish"
    else:
        label = "neutral"

    return compound, label


async def _modal_score_async(text: str) -> tuple[float, str]:
    """
    Call the Modal-hosted FinBERT function asynchronously.
    Falls back to local VADER if the Modal call fails.
    """
    try:
        from nlp.modal_scorer import finbert_score
        import asyncio
        loop = asyncio.get_event_loop()
        # modal .remote() is synchronous; run it in a thread pool
        result = await loop.run_in_executor(None, finbert_score.remote, text)
        return result
    except Exception as e:
        logger.warning(f"Modal inference failed ({e}), falling back to VADER")
        return _vader_score(text)


def _finbert_score(text: str) -> tuple[float, str]:
    """
    FinBERT sentiment: fine-tuned on financial text.
    Returns (score, label) where score is signed [-1, 1].
    """
    pipeline = _get_finbert()
    if pipeline is None:
        return _vader_score(text)  # fallback

    try:
        result = pipeline(text[:512])[0]
        label_raw = result["label"].lower()  # "positive" | "negative" | "neutral"
        confidence = result["score"]

        if label_raw == "positive":
            return confidence, "bullish"
        elif label_raw == "negative":
            return -confidence, "bearish"
        else:
            return 0.0, "neutral"
    except Exception as e:
        logger.warning(f"FinBERT scoring failed: {e}")
        return _vader_score(text)