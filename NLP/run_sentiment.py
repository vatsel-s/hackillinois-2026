"""
Running script for NLP/sentiment.py — measures end-to-end latency of score_and_write.

Usage:
    python NLP/run_sentiment.py
    python NLP/run_sentiment.py --csv NLP/test_articles.csv
"""

import csv
import time
import argparse
import sys
import os

# Allow running from project root or NLP/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from NLP.sentiment import score_and_write


def clear_processed(csv_path: str, n_processed: int):
    """Remove the first n_processed rows from csv_path.

    Rows appended by the news runner while scoring was in progress are preserved.
    """
    try:
        with open(csv_path, "r", newline="", encoding='utf-8') as f:
            lines = f.readlines()
        # lines[0] is the header; skip the first n_processed data rows after it
        header = lines[:1]
        remaining = lines[1 + n_processed:]
        with open(csv_path, "w", newline="", encoding='utf-8') as f:
            f.writelines(header + remaining)
        print(f"Cleared {n_processed} processed rows ({len(remaining)} remaining in {csv_path})")
    except FileNotFoundError:
        pass

def load_articles(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Normalize column names so both input.csv and test_articles.csv work
    normalized = []
    for row in rows:
        normalized.append({
            "timestamp":      row.get("timestamp", ""),
            "source":         row.get("source", ""),
            "headline":       row.get("headline") or row.get("title", ""),
            "content_header": row.get("content_header", ""),
            "link":           row.get("link") or row.get("url", ""),
            "ticker":         row.get("ticker") or row.get("matched_ticker", "N/A"),
            "confidence":     row.get("confidence") or row.get("match_confidence", "0.0")
        })
    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="input.csv")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Optionally split into smaller batches to compare latency")
    args = parser.parse_args()

    articles = load_articles(args.csv)
    print(f"Loaded {len(articles)} articles from {args.csv}\n")

    if not articles:
        print("Nothing to score.")
        return

    if args.batch_size:
        batches = [articles[i:i + args.batch_size]
                   for i in range(0, len(articles), args.batch_size)]
    else:
        batches = [articles]

    total_start = time.perf_counter()

    for i, batch in enumerate(batches):
        batch_start = time.perf_counter()
        results = score_and_write(batch)
        elapsed = time.perf_counter() - batch_start

        print(f"Batch {i + 1}/{len(batches)} — {len(batch)} articles in {elapsed:.2f}s "
              f"({elapsed / len(batch):.3f}s/article)")
        for r in results:
            signal_str = {1: "POSITIVE", -1: "NEGATIVE", 0: "NEUTRAL"}[r["signal"]]
            ticker = r.get("ticker", "N/A")
            conf = r.get("confidence", "0.0")
            print(f"  [{ticker:10s} | {signal_str:8s} {r['score']:.3f}]  {r['headline'][:80]}")
        print()

    total = time.perf_counter() - total_start
    total_articles = sum(len(b) for b in batches)
    print(f"Total: {total_articles} articles in {total:.2f}s "
          f"({total / total_articles:.3f}s/article)")
    print(f"Results written to: sentiment_output.csv")

    clear_processed(args.csv, total_articles)


if __name__ == "__main__":
    main()
