"""
Main orchestration loop for the HackIllinois 2026 Kalshi trading algorithm.

Pipeline (every 10s):
  1. poll_news()         — fetch new headlines from 30+ RSS feeds
  2. score_and_write()   — FinBERT sentiment via Modal GPU (label/score/signal)
  3. find_ticker()       — match headline to best Kalshi market  [teammate's module]
  4. resolve_signal()    — LLM direction inference (Groq + Llama 3.3 70B)
                           • financial markets → use FinBERT signal directly
                           • political/sports/other → use LLM for context-aware direction
  5. place_limit_order() — execute trade on Kalshi demo API

Signal routing:
  | Market type      | Signal source  |
  |------------------|----------------|
  | Financial/macro  | FinBERT        |
  | Political/sports | LLM (Groq)     |

Trade is skipped if: finbert_score < 0.70, or final_signal == 0.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from News.rss import poll_news, load_seen_links
from NLP.sentiment import score_and_write
from LLM.llm_signal import resolve_signal
from Kalshi.kalshi_order_executor import place_limit_order

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
POLL_INTERVAL_S = 10          # seconds between news polls
MIN_FINBERT_SCORE = 0.70      # minimum FinBERT confidence to act on
ORDER_COUNT = 1               # contracts per trade
ORDER_PRICE_CENTS = 50        # limit price proxy (market order)

# Ticker matcher — teammate's module (import when ready)
# from Kalshi.ticker_matcher import find_ticker
def find_ticker(headline: str, signal: int) -> dict | None:
    """
    Placeholder — replace with teammate's implementation.

    Expected return:
        {
            "ticker":       str,   # e.g. "KXFED-25-0525"
            "side":         str,   # "yes" or "no"
            "confidence":   float, # 0-1
            "market_title": str,   # e.g. "Will the Fed raise rates in March?"
        }
    Or None if no good match found.
    """
    return None  # TODO: replace with Kalshi/ticker_matcher.py


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
def main():
    print("Starting HackIllinois 2026 trading loop...")
    seen = load_seen_links()

    while True:
        try:
            articles = poll_news(seen).to_dict("records")
        except Exception as e:
            print(f"[news] Error polling feeds: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        if not articles:
            time.sleep(POLL_INTERVAL_S)
            continue

        print(f"[news] {len(articles)} new article(s)")

        try:
            scored = score_and_write(articles)
        except Exception as e:
            print(f"[nlp]  Error scoring articles: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        for row in scored:
            headline = row["headline"]
            finbert_signal = row["signal"]
            finbert_score = row["score"]

            # Skip low-confidence or neutral FinBERT results early
            if finbert_score < MIN_FINBERT_SCORE or finbert_signal == 0:
                continue

            # Find matching Kalshi market
            match = find_ticker(headline, finbert_signal)
            if not match:
                continue

            ticker = match["ticker"]
            market_title = match.get("market_title", "")

            # Resolve final trading signal (LLM overrides for non-financial markets)
            direction = resolve_signal(
                headline=headline,
                market_question=market_title,
                finbert_signal=finbert_signal,
            )

            final_signal = direction["signal"]
            print(
                f"[signal] {final_signal:+d} ({direction['source']})  "
                f"{ticker}  |  {headline[:60]}"
            )
            print(f"         reason: {direction['reasoning']}")

            if final_signal == 0:
                continue  # LLM says no clear edge — skip

            side = "yes" if final_signal == 1 else "no"
            place_limit_order(ticker, side, ORDER_COUNT, ORDER_PRICE_CENTS)

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
