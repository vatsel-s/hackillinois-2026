const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/proxy";
const FETCH_TIMEOUT_MS = 5000;

async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(id);
  }
}

export type NewsArticle = {
  source: string;
  headline: string;
  content_header: string;
  date: string;
  timestamp: number;
  link: string;
  sentiment?: "positive" | "negative" | "neutral";
  sentiment_score?: number;
};

export type TickerSnapshot = {
  market_ticker: string;
  yes_bid: number;
  yes_ask: number;
  last_updated?: number;
};

export type OrderRequest = {
  ticker: string;
  side: "yes" | "no";
  count: number;
  price_cents: number;
};

export type OrderResult = {
  success: boolean;
  order_id?: string;
  error?: string;
};

export async function fetchNews(limit = 50): Promise<NewsArticle[]> {
  const res = await fetchWithTimeout(`${API_BASE}/news?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch news");
  return res.json();
}

export async function fetchTickers(): Promise<TickerSnapshot[]> {
  const res = await fetchWithTimeout(`${API_BASE}/tickers`);
  if (!res.ok) throw new Error("Failed to fetch tickers");
  return res.json();
}

export async function fetchSentiment(text: string): Promise<{ label: string; score: number }> {
  const res = await fetchWithTimeout(`${API_BASE}/sentiment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("Failed to get sentiment");
  return res.json();
}

export async function placeOrder(order: OrderRequest): Promise<OrderResult> {
  const res = await fetchWithTimeout(`${API_BASE}/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(order),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { success: false, error: data.detail || res.statusText };
  return { success: true, ...data };
}

export function getTickerWsUrl(): string {
  if (typeof window === "undefined") return "";
  const base = process.env.NEXT_PUBLIC_WS_URL || "";
  return base ? `${base}/ws/tickers` : "/ws/proxy";
}
