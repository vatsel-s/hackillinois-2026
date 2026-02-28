"""
signal/kalshi_signal.py — Convert NLP-scored events into Kalshi trading signals.

This is where the NLP scores become actionable YES/NO positions on Kalshi.
The logic here is intentionally simple — you should tune it based on your
backtesting results. The structure supports adding more sophisticated
position sizing, cooldowns, and market-specific logic.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from utils.models import NewsEvent

logger = logging.getLogger("signal")


@dataclass
class KalshiSignal:
    """A trading signal for a specific Kalshi market."""
    timestamp: datetime
    market_category: str          # e.g. "FED_RATE", "ELECTION"
    direction: str                # "YES" | "NO"
    confidence: float             # 0.0 – 1.0
    sentiment_score: float        # raw signed sentiment (-1 to +1)
    source_event_uid: str
    headline: str
    url: str
    reasoning: str

    def __str__(self):
        return (
            f"[SIGNAL] {self.direction} {self.market_category} "
            f"| conf={self.confidence:.2f} | sent={self.sentiment_score:+.2f} "
            f"| {self.headline[:60]}"
        )


# ── Market-specific direction logic ──────────────────────────────────────────
# For each Kalshi market category, define what "bullish" sentiment means
# in terms of YES/NO on the most common contract type.
#
# Example: FED_RATE — a "bullish" (positive) sentiment about the economy
# (e.g., "strong jobs growth") → Fed LESS likely to cut → "NO" on rate cuts.
# A "bearish" (negative) sentiment → Fed MORE likely to cut → "YES" on rate cuts.
#
# You need to map these carefully per contract — the defaults below are
# reasonable starting points but should be tuned to exact contract wording.

MARKET_DIRECTION_LOGIC = {
    # "YES" = rate cut happens. Negative economic news → rate cut more likely.
    "FED_RATE":       {"positive_maps_to": "NO",  "negative_maps_to": "YES"},

    # "YES" = unemployment rises. Negative jobs news → unemployment rises.
    "JOBS":           {"positive_maps_to": "NO",  "negative_maps_to": "YES"},

    # "YES" = a specific candidate wins. Positive news about them → YES.
    # NOTE: You'd want separate signals per candidate — this is a placeholder.
    "ELECTION":       {"positive_maps_to": "YES", "negative_maps_to": "NO"},

    # "YES" = market falls below threshold. Negative news → YES.
    "MARKETS":        {"positive_maps_to": "NO",  "negative_maps_to": "YES"},

    # "YES" = team wins. Positive news about team → YES.
    "SPORTS_MLB":     {"positive_maps_to": "YES", "negative_maps_to": "NO"},
    "SPORTS_NFL":     {"positive_maps_to": "YES", "negative_maps_to": "NO"},

    # "YES" = BTC above threshold. Positive crypto news → YES.
    "CRYPTO":         {"positive_maps_to": "YES", "negative_maps_to": "NO"},

    # "YES" = conflict escalates / oil prices spike. Negative news → YES.
    "GEOPOLITICAL":   {"positive_maps_to": "NO",  "negative_maps_to": "YES"},
}


def generate_signals(event: NewsEvent) -> list[KalshiSignal]:
    """
    Convert a scored NewsEvent into a list of KalshiSignals (one per matched market).
    Returns empty list if event doesn't clear signal threshold.
    """
    signals = []

    if event.signal_score is None or event.signal_score < 0.01:
        return signals

    # Use article sentiment if available (Stage 2), else headline sentiment
    sentiment = (
        event.article_sentiment
        if event.article_sentiment is not None
        else event.headline_sentiment or 0.0
    )

    for market in event.matched_markets:
        logic = MARKET_DIRECTION_LOGIC.get(market)
        if not logic:
            continue

        if sentiment >= 0.05:
            direction = logic["positive_maps_to"]
        elif sentiment <= -0.05:
            direction = logic["negative_maps_to"]
        else:
            # Neutral — don't generate a signal for this market
            continue

        # Confidence = signal_score, scaled by source reliability
        source_weight = _source_weight(event.source)
        confidence = min(event.signal_score * source_weight, 1.0)

        reasoning = (
            f"Source={event.source} | "
            f"headline_sent={event.headline_sentiment:+.2f} | "
            f"article_sent={'N/A' if event.article_sentiment is None else f'{event.article_sentiment:+.2f}'} | "
            f"signal_score={event.signal_score:.2f}"
        )

        signal = KalshiSignal(
            timestamp=datetime.now(timezone.utc),
            market_category=market,
            direction=direction,
            confidence=confidence,
            sentiment_score=sentiment,
            source_event_uid=event.uid,
            headline=event.headline,
            url=event.url,
            reasoning=reasoning,
        )

        signals.append(signal)
        logger.info(str(signal))

    return signals


def _source_weight(source: str) -> float:
    """
    Weight signal confidence by source reliability.
    Alpaca/RSS from major outlets = most reliable.
    Reddit = lower weight (more noise).
    GDELT = medium (many sources, less curated).
    """
    return {
        "alpaca": 1.00,
        "rss":    0.90,
        "gdelt":  0.75,
        "reddit": 0.55,
    }.get(source, 0.70)