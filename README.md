# hackillinois-2026

News-driven Kalshi prediction market pipeline: RSS → sentiment (FinBERT on Modal) → Kalshi markets/orders.

## Quick start

### Backend (FastAPI)

From repo root, with a venv and `pip install -r requirements.txt`:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Optional: set `.env` with `KALSHI_API_KEY` and `KALSHI_PRIVATE_KEY` for live orders; run the RSS pipeline for real news.

### Frontend (Next.js)

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000. The app proxies API calls to the backend at port 8000.

## Structure

- **backend/** – FastAPI server: `/api/news`, `/api/tickers`, `/api/sentiment`, `/api/orders`.
- **frontend/** – Next.js dashboard: Dashboard, Markets, News, Place Order.
- **Kalshi/** – Auth, order execution, ticker WebSocket.
- **News/** – RSS polling, GDELT.
- **NLP/** – FinBERT sentiment via Modal.
