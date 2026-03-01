"""
Main orchestration loop for the HackIllinois 2026 Kalshi trading algorithm.

Pipeline (every 10s):
  1. poll_news()         — fetch new headlines from 30+ RSS feeds
  2. match_tickers()     — match each headline to a Kalshi market (Modal GPU)
  3. score_articles()    — FinBERT sentiment via Modal GPU (finbert_label/score/signal)
  4. resolve_signal()    — LLM direction inference (Groq + Llama 3.3 70B)
                           • financial markets → use FinBERT signal directly
                           • political/sports/other → use LLM for context-aware direction
  5. write_decisions()   — append full row (all 16 fields) to sentiment_output.csv
  6. print decision      — output to terminal (Kalshi order execution coming soon)

Signal routing:
  | Market type      | Signal source  |
  |------------------|----------------|
  | Financial/macro  | FinBERT        |
  | Political/sports | LLM (Groq)     |

Trade is skipped if: finbert_score < 0.70, signal == 0, or ticker confidence < 0.30.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from News.rss import poll_news, load_seen_links
from NLP.ticker_modal import match_tickers
from NLP.sentiment import score_articles, write_decisions
from LLM.llm_signal import resolve_signal

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
POLL_INTERVAL_S = 10          # seconds between news polls
MIN_FINBERT_SCORE = 0.70      # minimum FinBERT confidence to act on
MIN_TICKER_CONFIDENCE = 0.30  # minimum ticker match confidence to act on


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
def main():
    print("Starting HackIllinois 2026 trading loop...")
    seen = load_seen_links()

    while True:
        # --- 1. Fetch new headlines ---
        try:
            df = poll_news(seen)
        except Exception as e:
            print(f"[news] Error polling feeds: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        if df.empty:
            time.sleep(POLL_INTERVAL_S)
            continue

        print(f"[news] {len(df)} new article(s)")

        # Normalize column names to match downstream expectations
        df = df.rename(columns={"title": "headline", "content": "content_header"})
        articles = df.to_dict("records")

        # --- 2. Match each headline to a Kalshi market ---
        try:
            headlines = [a["headline"] for a in articles]
            ticker_matches = match_tickers(headlines)
        except Exception as e:
            print(f"[ticker] Error matching tickers: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        for article, match in zip(articles, ticker_matches):
            article["ticker"] = match["ticker"]
            article["market_title"] = match["market_title"]
            article["confidence"] = match["confidence"]

        # --- 3. Score with FinBERT (no CSV write yet) ---
        try:
            scored = score_articles(articles)
        except Exception as e:
            print(f"[nlp]  Error scoring articles: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        # --- 4, 5, 6. LLM signal → write full row → print decision ---
        for row in scored:
            headline          = row["headline"]
            finbert_signal    = row["finbert_signal"]
            finbert_score     = row["finbert_score"]
            ticker            = row["ticker"]
            market_title      = row["market_title"]
            ticker_confidence = row["ticker_confidence"]

            # Skip low-confidence or neutral results
            if finbert_score < MIN_FINBERT_SCORE:
                continue
            if finbert_signal == 0:
                continue
            if ticker_confidence < MIN_TICKER_CONFIDENCE:
                continue

            direction = resolve_signal(
                headline=headline,
                market_question=market_title,
                finbert_signal=finbert_signal,
            )

            final_signal = direction["signal"]
            side = "YES" if final_signal == 1 else ("NO" if final_signal == -1 else "SKIP")

            # Write complete row to sentiment_output.csv
            write_decisions([{
                **row,
                "llm_signal":     direction["signal"],
                "llm_source":     direction["source"],
                "llm_reasoning":  direction["reasoning"],
                "final_signal":   final_signal,
                "final_decision": side,
            }])

            print(
                f"\n[decision] {side}  |  {ticker}  (ticker conf: {ticker_confidence:.2f})"
            )
            print(f"  headline:  {headline[:80]}")
            print(f"  market:    {market_title[:80]}")
            print(f"  finbert:   {row['finbert_label']} {finbert_score:.3f}  signal={finbert_signal:+d}")
            print(f"  llm/src:   {direction['source']}  signal={final_signal:+d}")
            print(f"  reason:    {direction['reasoning']}")

            if final_signal == 0:
                continue  # No clear edge — skip

            # TODO: place_limit_order(ticker, side.lower(), count, price_cents)

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
