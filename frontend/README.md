# Kalshi News Frontend

Next.js dashboard for the news-driven Kalshi prediction market pipeline.

## Setup

```bash
cd frontend
npm install
```

## Run

1. **Start the backend** (from repo root):

   ```bash
   cd ..
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend**:

   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000).

The frontend proxies `/api/proxy/*` to `http://127.0.0.1:8000/api/*`, so the backend must be running for news, tickers, sentiment, and orders to work.

## Pages

- **Dashboard** – Overview: live tickers and latest news.
- **Markets** – Ticker cards with bid/ask (refreshes every 5s).
- **News** – Full news feed from RSS pipeline (with optional sentiment badges).
- **Place Order** – Form to submit limit orders to Kalshi (via backend).

## Env (optional)

- `NEXT_PUBLIC_API_URL` – Override API base (default: `/api/proxy`).
- `NEXT_PUBLIC_WS_URL` – WebSocket base for live tickers (e.g. `http://localhost:8000`).
