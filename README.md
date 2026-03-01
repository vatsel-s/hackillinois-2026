# HackIllinois 2026 — Kalshi News Trading Bot

An autonomous trading system that reads real-time financial news, runs multi-stage NLP/LLM analysis on GPU-accelerated cloud infrastructure, and executes limit orders on [Kalshi](https://kalshi.com) prediction markets.

---

## How It Works

```
RSS Feeds (25+)
      │
      ▼
  News Ingestion              News/rss.py
      │  deduplicated by URL hash
      ▼
  Ticker Matching             NLP/ticker_modal.py
      │  SentenceTransformers (all-MiniLM-L6-v2) on Modal T4 GPU
      │  matches headlines → Kalshi market tickers
      ▼
  Financial Sentiment         NLP/sentiment.py
      │  ProsusAI/FinBERT on Modal A10G GPU
      │  returns label + confidence score
      ▼
  LLM Signal Routing          LLM/llm_signal.py
      │  Groq API · Llama 3.3 70B
      │  resolves ambiguous signals with full article context
      ▼
  Order Execution             Kalshi/kalshi_order_executor.py
      │  RSA-PSS signed REST requests
      │  places YES/NO limit orders at best ask
      ▼
  Sell Heartbeat              Kalshi/sell_heartbeat.py
         background thread · monitors open positions · closes on reversal
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Financial Sentiment | [ProsusAI/FinBERT](https://huggingface.co/ProsusAI/finbert) |
| Market Matching | SentenceTransformers `all-MiniLM-L6-v2` |
| GPU Inference | [Modal](https://modal.com) — A10G (FinBERT) · T4 (embeddings) |
| LLM Routing | [Groq API](https://groq.com) — Llama 3.3 70B Versatile |
| Prediction Markets | [Kalshi REST API](https://kalshi.com) — RSA-PSS authenticated |
| News Ingestion | feedparser — 25+ RSS feeds |
| Backend | Flask + SSE (Server-Sent Events) |
| Frontend | React + Vite + Three.js |
| Frontend Hosting | Vercel |
| Backend Hosting | Railway |

---

## Project Structure

```
.
├── main.py                       # Orchestration loop
├── api/
│   └── index.py                  # Flask API (start/pause/status/logs/news SSE)
├── News/
│   └── rss.py                    # RSS polling + deduplication
├── NLP/
│   ├── ticker_modal.py           # Modal-powered market ticker matching
│   └── sentiment.py              # Modal-powered FinBERT sentiment
├── LLM/
│   └── llm_signal.py             # Groq/Llama 3.3 70B signal resolver
├── Kalshi/
│   ├── kalshi_auth.py            # RSA-PSS request signing
│   ├── kalshi_order_executor.py  # Limit order placement
│   ├── market_utils.py           # Best ask price lookup
│   └── sell_heartbeat.py         # Background position monitor
├── Frontend/
│   └── HackIllinois-2026/        # React + Vite app
├── sentiment_output.csv          # Pipeline output log
├── requirements.txt
├── Procfile                      # Railway entrypoint
└── vercel.json                   # Vercel frontend build config
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Modal](https://modal.com) account (`modal token new`)
- A [Groq](https://groq.com) API key
- Kalshi API key + RSA private key

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Create a .env file at the repo root
cat > .env <<EOF
GROQ_API_KEY=your_groq_key
KALSHI_API_KEY=your_kalshi_key
KALSHI_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
EOF

# Start the Flask API server (port 8000)
python api/index.py
```

### Frontend

```bash
cd Frontend/HackIllinois-2026
npm install
npm run dev          # starts Vite dev server on port 5173
```

Open [http://localhost:5173](http://localhost:5173). The Vite proxy forwards `/api/*` to `localhost:8000`.

Click **Start** in the dashboard to launch the trading pipeline.

---

## Deployment

### Backend → Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Set environment variables in the Railway dashboard:
   - `GROQ_API_KEY`
   - `KALSHI_API_KEY`
   - `KALSHI_PRIVATE_KEY`
   - `PORT=8000`
3. Railway reads `Procfile` and runs `python api/index.py` automatically.
4. Copy the Railway public URL (e.g. `https://your-app.railway.app`).

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → import this GitHub repo
2. Set the following in Vercel project settings:
   - **Build command:** `cd Frontend/HackIllinois-2026 && npm install && npm run build`
   - **Output directory:** `Frontend/HackIllinois-2026/dist`
   - **Environment variable:** `VITE_API_BASE=https://your-app.railway.app`
3. Deploy. Vercel serves the static frontend; all API calls route to Railway.

> **Note:** The Flask backend cannot run on Vercel — it requires long-lived processes,
> subprocess spawning, file writes, and packages (`torch`, `transformers`) that exceed
> Vercel's 250 MB bundle limit. Modal GPU inference runs on Modal's own cloud regardless
> of where the backend is hosted.

---

## Environment Variables

| Variable | Where | Description |
|---|---|---|
| `GROQ_API_KEY` | Backend | Groq API key for Llama 3.3 70B |
| `KALSHI_API_KEY` | Backend | Kalshi exchange API key |
| `KALSHI_PRIVATE_KEY` | Backend | PEM-encoded RSA private key for request signing |
| `PORT` | Backend | Flask listen port (default `8000`) |
| `VITE_API_BASE` | Frontend (build) | Railway backend URL (empty string for local dev) |

---

## Pipeline Configuration

Edit constants at the top of `main.py`:

```python
POLL_INTERVAL_S       = 10    # seconds between RSS polls
MIN_FINBERT_SCORE     = 0.70  # minimum FinBERT confidence to act on
MIN_TICKER_CONFIDENCE = 0.40  # minimum market match confidence to act on
```

Order sizing and take-profit/stop-loss thresholds are configurable via the dashboard UI at runtime (sent to `/api/thresholds`).
