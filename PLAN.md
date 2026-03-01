# HackIllinois 2026 — Trading Algorithm Plan

## Goal
Automatically trade Kalshi prediction market contracts by detecting sentiment in breaking news headlines, finding the most relevant open market, and placing a buy/sell order — all in near real-time.

---

## Full Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN LOOP (every 10s)                    │
│                                                                 │
│  News/rss.py          NLP/sentiment.py       Ticker Matcher     │
│  ──────────           ───────────────        ──────────────     │
│  poll_news()    ───►  score_and_write()  ───► find_ticker()     │
│  30+ RSS feeds        Modal GPU (FinBERT)     Kalshi REST API   │
│  → new articles       → label/score/signal    → best ticker     │
│                       → appends to CSV        → side (yes/no)   │
│                                                    │            │
│                                                    ▼            │
│                              Kalshi/kalshi_order_executor.py    │
│                              place_limit_order(ticker, side,    │
│                                               count, price)     │
└─────────────────────────────────────────────────────────────────┘
```

### Decision Logic
| Sentiment | Signal | Action |
|-----------|--------|--------|
| positive  | +1     | buy YES on matched ticker |
| negative  | -1     | buy NO on matched ticker |
| neutral   | 0      | skip — no trade |

Confidence threshold: only trade if `score >= 0.70` (configurable).

---

## Status

### ✅ Done

#### News Ingestion — `News/rss.py`
- Polls 30+ RSS feeds (WSJ, Bloomberg, CNBC, BBC, NYT, etc.) every 10s
- Deduplicates via `seen_links.txt`
- Returns a pandas DataFrame: `source, headline, content_header, date, timestamp, link`

#### NLP Inference — `NLP/modaltest.py` + `NLP/sentiment.py`
- **`NLP/modaltest.py`**: Modal deployment using `@app.cls` with `@modal.enter()` — FinBERT model loads once per container, not per call
- `score(text)` — single headline inference
- `score_batch(texts)` — batch inference in one GPU call (fast)
- Returns `{label, score, signal}` where signal = +1 / 0 / -1
- **`NLP/sentiment.py`**: importable Python module — any file can do `from NLP.sentiment import score_and_write`
- `score_and_write(articles)` — scores a batch and appends to `sentiment_output.csv`

#### Kalshi Order Execution — `Kalshi/kalshi_order_executor.py`
- RSA-signed auth via `Kalshi/kalshi_auth.py`
- `place_limit_order(ticker, side, count, price_cents)` — places a limit order on Kalshi demo API

#### Kalshi Market Streaming — `Kalshi/kalshi_ticker_watcher.py`
- WebSocket stream for live bid/ask prices on any list of tickers

---

### ❌ Still Needed

#### 1. Ticker Matcher — `Kalshi/ticker_matcher.py` *(teammate's task)*
The critical missing link. Given a headline + signal, find the best Kalshi market to trade.

**Steps:**
1. Fetch all open Kalshi markets via REST: `GET /trade-api/v2/markets`
2. Store market list (title + ticker) — refresh periodically
3. Match headline to market using semantic similarity or keyword overlap
4. Return `(ticker, side)` where side = "yes" if signal == +1, "no" if signal == -1

**Input:**
```python
{
  "headline": "Fed raises rates by 50bps",
  "signal": -1,
  "label": "negative",
  "score": 0.88
}
```
**Output:**
```python
{ "ticker": "KXFED-25-0525", "side": "no", "confidence": 0.88 }
```

**Interface (what it should export):**
```python
# Kalshi/ticker_matcher.py
def find_ticker(headline: str, signal: int) -> dict | None:
    """Returns {'ticker': str, 'side': str} or None if no good match found."""
```

#### 2. Main Orchestrator — `main.py`
Ties everything together in one loop.

```python
# Pseudocode
from News.rss import poll_news, load_seen_links
from NLP.sentiment import score_and_write
from Kalshi.ticker_matcher import find_ticker
from Kalshi.kalshi_order_executor import place_limit_order

seen = load_seen_links()
while True:
    articles = poll_news(seen).to_dict("records")
    if articles:
        scored = score_and_write(articles)   # GPU inference on Modal
        for row in scored:
            if row["signal"] == 0 or row["score"] < 0.70:
                continue                      # skip neutral / low-confidence
            match = find_ticker(row["headline"], row["signal"])
            if match:
                place_limit_order(
                    ticker=match["ticker"],
                    side=match["side"],
                    count=1,
                    price_cents=50           # market order proxy
                )
    time.sleep(10)
```

#### 3. Deploy Modal App
```bash
modal deploy NLP/modaltest.py
```
Must be re-deployed after the `@app.cls` refactor before `sentiment.py` will work.

#### 4. Wire `rss.py` into the main loop
Replace the `# TODO` comment in `News/rss.py` line 131 — or just use `main.py` above and call `poll_news` directly from there.

---

## CSV Interface (`sentiment_output.csv`)
The CSV is the handoff point between NLP and the ticker matcher. Columns:

| Column | Type | Description |
|--------|------|-------------|
| timestamp | int | Unix timestamp of article |
| source | str | Feed name (e.g. "WSJ MARKETS") |
| headline | str | Article headline |
| content_header | str | First 500 chars of article |
| link | str | Article URL |
| label | str | "positive" / "negative" / "neutral" |
| score | float | FinBERT confidence 0–1 |
| signal | int | +1 / 0 / -1 |

The ticker matcher reads this CSV (or receives rows directly via function call) to decide what to trade.

---

## Potential Improvements

### Context-Aware Direction Inference ("Trump Effect" Fix)
**Problem:** Sentiment ≠ market direction. FinBERT scores the *tone* of a headline, but for political/event markets the tone can be misleading. "Trump indicted on 4 counts" is `negative` — but it likely *increases* the probability of "Will Trump win the primary?" because controversy historically rallies his base.

**Solution: Two-stage inference**

| Stage | Model | Input | Output |
|-------|-------|-------|--------|
| 1 (current) | FinBERT | headline | `{label, score, signal}` |
| 2 (proposed) | LLM (Claude Haiku) | headline + Kalshi market question | direction `+1 / 0 / -1` |

Stage 2 replaces blind sentiment-to-signal mapping with context-aware inference that understands what each specific market is asking.

**Example:**
```
Headline:        "Trump indicted on 4 counts"
Market question: "Will Trump win the 2024 Republican primary?"

LLM prompt: "Does this headline make YES more or less likely? Output +1, -1, or 0."
→ +1  (historically, attacks rally his base)
```

**Implementation:** Add a second Modal function (CPU is fine, fast LLM call) that takes `(headline, market_question)` and returns a direction. The market question already comes from the ticker matcher, so no extra data is needed.

**When to use each approach:**
- Financial markets (Fed rates, earnings, macro) → keep FinBERT signal directly
- Political/event markets → use LLM direction inference

**Other signals worth adding (lower priority):**
- **Novelty decay**: 5th headline about the same story → market already priced it in, skip
- **Source weighting**: Bloomberg/WSJ headline > ESPN headline
- **Recency decay**: weight headlines by age within the polling window

---

## Key Files

| File | Status | Purpose |
|------|--------|---------|
| `News/rss.py` | ✅ done | Poll 30+ RSS feeds |
| `NLP/modaltest.py` | ✅ done | Modal GPU deployment (FinBERT) |
| `NLP/sentiment.py` | ✅ done | Importable API + CSV writer |
| `Kalshi/kalshi_auth.py` | ✅ done | RSA auth headers |
| `Kalshi/kalshi_order_executor.py` | ✅ done | Place limit orders |
| `Kalshi/kalshi_ticker_watcher.py` | ✅ done | Live bid/ask WebSocket stream |
| `Kalshi/ticker_matcher.py` | ❌ needed | Match headline → Kalshi ticker |
| `main.py` | ❌ needed | Main orchestration loop |
