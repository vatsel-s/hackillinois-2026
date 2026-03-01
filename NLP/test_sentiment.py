"""
Test script for NLP/sentiment.py — measures end-to-end latency of score_and_write.

Usage:
    python NLP/test_sentiment.py
    python NLP/test_sentiment.py --csv NLP/test_articles.csv
"""

import csv
import time
import argparse
import sys
import os

# Allow running from project root or NLP/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from NLP.sentiment import score_and_write


def load_articles(csv_path: str) -> list[dict]:
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="NLP/test_articles.csv")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Optionally split into smaller batches to compare latency")
    args = parser.parse_args()

    articles = load_articles(args.csv)
    print(f"Loaded {len(articles)} articles from {args.csv}\n")

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
            print(f"  [{signal_str:8s} {r['score']:.3f}]  {r['headline'][:80]}")
        print()

    total = time.perf_counter() - total_start
    total_articles = sum(len(b) for b in batches)
    print(f"Total: {total_articles} articles in {total:.2f}s "
          f"({total / total_articles:.3f}s/article)")
    print(f"Results written to: sentiment_output.csv")


if __name__ == "__main__":
    main()
