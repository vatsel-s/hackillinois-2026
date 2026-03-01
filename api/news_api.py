"""
api.py — FastAPI server for the enriched news pipeline.

Endpoints:
  GET  /news          – Return all rows from input.csv as JSON
  GET  /news/stream   – SSE stream; pushes new rows as they arrive
  GET  /news/latest   – Return the N most recent rows (query param: n=20)

Run with:
  uvicorn api.news_api:app --port 8001
"""

import asyncio
import os
import json
import pandas as pd
from typing import AsyncGenerator

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# ── Config ────────────────────────────────────────────────────────────────────
CSV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input.csv")
POLL_INTERVAL = 2  # seconds between CSV checks for SSE

app = FastAPI(title="Enriched News API")

# Allow all origins so any frontend (React, etc.) can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_csv() -> pd.DataFrame:
    """Read the pipeline CSV, returning an empty DataFrame if it doesn't exist yet."""
    if not os.path.isfile(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        return pd.DataFrame()
    return pd.read_csv(CSV_FILE, encoding="utf-8")


def df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to a list of dicts, filling NaN with None."""
    return df.where(pd.notnull(df), None).to_dict(orient="records")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/news")
def get_all_news():
    """Return every article currently in the CSV."""
    df = read_csv()
    return {"count": len(df), "articles": df_to_records(df)}


@app.get("/news/latest")
def get_latest_news(n: int = Query(default=20, ge=1, le=500)):
    """Return the N most recent articles (tail of the CSV)."""
    df = read_csv()
    if df.empty:
        return {"count": 0, "articles": []}
    latest = df.tail(n)
    return {"count": len(latest), "articles": df_to_records(latest)}


async def sse_generator() -> AsyncGenerator[str, None]:
    """
    Server-Sent Events generator.
    Polls the CSV every POLL_INTERVAL seconds and pushes any new rows
    to connected clients as JSON-encoded SSE events.
    """
    last_row_count = 0

    while True:
        await asyncio.sleep(POLL_INTERVAL)
        df = read_csv()
        current_count = len(df)

        if current_count > last_row_count:
            new_rows = df.iloc[last_row_count:]
            for record in df_to_records(new_rows):
                payload = json.dumps(record, default=str)
                yield f"data: {payload}\n\n"
            last_row_count = current_count


@app.get("/news/stream")
async def stream_news():
    """
    SSE endpoint — connect with EventSource in the browser:

        const es = new EventSource("http://localhost:8000/news/stream");
        es.onmessage = (e) => console.log(JSON.parse(e.data));
    """
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering if behind a proxy
        },
    )
