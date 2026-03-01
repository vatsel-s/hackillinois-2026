"""
Unified news runner.
- RSS:  polls every 10 seconds  (fast, incremental)
- GKG:  fetches every 15 minutes (GDELT update cadence)
Both append to input.csv with a shared schema: timestamp, title, content
"""

import time
import threading
import pandas as pd

from gkg_test import extract_clean_df
from rss import poll_news, load_seen_links

CSV_FILE = "input.csv"
GKG_INTERVAL = 15 * 60   # 900 seconds
RSS_INTERVAL = 10         # seconds


def _append(df: pd.DataFrame):
    """Append a dataframe (3 columns: timestamp, title, content) to the shared CSV."""
    df.to_csv(CSV_FILE, mode="a", header=False, index=False)


def gkg_loop():
    while True:
        try:
            print("[GKG] Fetching latest GDELT GKG snapshot...")
            raw = extract_clean_df()          # columns: timestamp, title, themes
            out = raw.rename(columns={"themes": "content"})
            _append(out)
            print(f"[GKG] Appended {len(out)} rows to {CSV_FILE}")
        except Exception as e:
            print(f"[GKG] Error: {e}")
        time.sleep(GKG_INTERVAL)


def rss_loop(seen_links: set):
    while True:
        try:
            poll_news(seen_links)             # appends internally; also returns df
        except Exception as e:
            print(f"[RSS] Error: {e}")
        time.sleep(RSS_INTERVAL)


if __name__ == "__main__":
    print("Starting unified news pipeline...")
    print(f"  RSS  -> every {RSS_INTERVAL}s")
    print(f"  GKG  -> every {GKG_INTERVAL // 60} min")
    print(f"  Output -> {CSV_FILE}\n")

    seen = load_seen_links()

    # GKG runs in a background daemon thread
    gkg_thread = threading.Thread(target=gkg_loop, daemon=True, name="GKG")
    gkg_thread.start()

    # RSS runs on the main thread (blocks forever)
    rss_loop(seen)
