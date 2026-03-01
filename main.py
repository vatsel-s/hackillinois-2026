"""
Main orchestration loop for the HackIllinois 2026 Kalshi trading algorithm.
Integrated with Order Execution and Portfolio Heartbeat.
"""

import time
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Existing Imports ---
from News.rss import poll_news, load_seen_links
from NLP.ticker_modal import match_tickers
from NLP.sentiment import score_articles, write_decisions
from LLM.llm_signal import resolve_signal

# --- New Trading Imports ---
# main.py
from Kalshi.sell_heartbeat import start_background_heartbeat
from Kalshi.kalshi_order_executor import execute_order
from Kalshi.market_utils import get_best_ask

# --------------------------------------------------------------------------
# Configuration (overridable via env vars)
# --------------------------------------------------------------------------
POLL_INTERVAL_S = 10          # seconds between news polls
MIN_FINBERT_SCORE = 0.70      # minimum FinBERT confidence to act on
MIN_TICKER_CONFIDENCE = 0.40  # minimum ticker match confidence to act on
TRADE_QUANTITY = 1            # Number of contracts to buy per signal
EXECUTION_PRICE = int(os.environ.get("MAX_BUY_PRICE", "60"))  # max cents willing to pay

# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
def main():
    print("Starting HackIllinois 2026 trading loop...")
    
    # 1. Mount the Heartbeat (Runs in background thread)
    print("[system] Mounting Portfolio Heartbeat...")
    start_background_heartbeat()
    
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
            # Heartbeat is still running in background while we wait
            time.sleep(POLL_INTERVAL_S)
            continue

        print(f"[news] {len(df)} new article(s)")

        # Normalize column names
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

        # --- 3. Score with FinBERT ---
        try:
            scored = score_articles(articles)
        except Exception as e:
            print(f"[nlp]  Error scoring articles: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        # --- 4, 5, 6. LLM signal → Write CSV → EXECUTE TRADE ---
        for row in scored:
            headline      = row["headline"]
            finbert_signal = row["finbert_signal"]
            finbert_score  = row["finbert_score"]
            ticker         = row["ticker"]
            market_title   = row["market_title"]
            ticker_confidence = row["ticker_confidence"]

            # Filter weak signals
            if finbert_score < MIN_FINBERT_SCORE: continue
            if finbert_signal == 0: continue
            if ticker_confidence < MIN_TICKER_CONFIDENCE: continue

            # Resolve Direction
            direction = resolve_signal(
                headline=headline,
                market_question=market_title,
                finbert_signal=finbert_signal,
            )

            final_signal = direction["signal"]
            side = "yes" if final_signal == 1 else ("no" if final_signal == -1 else "SKIP")
            
            # Write to CSV (Monitoring Log)
            write_decisions([{
                **row,
                "llm_signal":     direction["signal"],
                "llm_source":     direction["source"],
                "llm_reasoning":  direction["reasoning"],
                "final_signal":   final_signal,
                "final_decision": side.upper(),
            }])

            # Print Decision
            print(f"\n[decision] {side.upper()} | {ticker} (conf: {ticker_confidence:.2f})")
            print(f"  Reason: {direction['reasoning']}")

            # --- EXECUTION LOGIC ---
            if final_signal != 0:
                print(f"  >>> SIGNAL DETECTED: Initiating Buy for {side.upper()}...")

                side_real = "yes" if final_signal == 1 else "no"
                execution_price = EXECUTION_PRICE

                # A. Check current market ask against our max buy price
                best_ask = get_best_ask(ticker, side_real)
                if best_ask is not None and best_ask > EXECUTION_PRICE:
                    print(f"  >>> SKIPPING: Ask ({best_ask}¢) > Max Buy Price ({EXECUTION_PRICE}¢).")
                    continue

                if execution_price:
                    print(f"  >>> Placing limit buy at {execution_price}¢ (ask={best_ask}¢)")
                    
                    try:
                        # B. Place the Order
                        order_response = execute_order(
                            ticker=ticker,
                            action="buy",
                            side=side,
                            count=TRADE_QUANTITY,
                            type="limit",
                            price=execution_price
                        )
                        print(f"  >>> ORDER SENT! ID: {order_response.get('order', {}).get('order_id')}")
                        
                    except Exception as exc:
                        print(f"  >>> EXECUTION FAILED: {exc}")
                else:
                    print(f"  >>> SKIPPING: No liquidity (Ask price not found).")
            
        # Loop delay
        time.sleep(POLL_INTERVAL_S)

if __name__ == "__main__":
    main()