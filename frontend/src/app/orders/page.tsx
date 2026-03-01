"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchTickers, placeOrder, type OrderRequest } from "@/lib/api";

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const [ticker, setTicker] = useState("");
  const [side, setSide] = useState<"yes" | "no">("yes");
  const [count, setCount] = useState(1);
  const [priceCents, setPriceCents] = useState(50);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const { data: tickers = [] } = useQuery({
    queryKey: ["tickers"],
    queryFn: fetchTickers,
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ticker.trim()) {
      setMessage("Enter a ticker");
      setStatus("error");
      return;
    }
    setStatus("loading");
    setMessage("");
    const result = await placeOrder({
      ticker: ticker.trim(),
      side,
      count,
      price_cents: priceCents,
    });
    if (result.success) {
      setStatus("success");
      setMessage(`Order placed. ${result.order_id ? `ID: ${result.order_id}` : ""}`);
      queryClient.invalidateQueries({ queryKey: ["tickers"] });
    } else {
      setStatus("error");
      setMessage(result.error || "Order failed");
    }
  }

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Place Order</h1>
        <p className="text-[hsl(var(--muted))] mt-1">
          Submit a limit order to the Kalshi demo API (via backend)
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6 space-y-5"
      >
        <div>
          <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1">
            Market Ticker
          </label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="e.g. KXFED"
            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--accent))]"
            list="ticker-list"
          />
          <datalist id="ticker-list">
            {tickers.map((t) => (
              <option key={t.market_ticker} value={t.market_ticker} />
            ))}
          </datalist>
        </div>

        <div>
          <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1">
            Side
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="side"
                checked={side === "yes"}
                onChange={() => setSide("yes")}
                className="rounded-full border-[hsl(var(--border))] text-[hsl(var(--accent))] focus:ring-[hsl(var(--accent))]"
              />
              <span>Yes</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="side"
                checked={side === "no"}
                onChange={() => setSide("no")}
                className="rounded-full border-[hsl(var(--border))] text-[hsl(var(--accent))] focus:ring-[hsl(var(--accent))]"
              />
              <span>No</span>
            </label>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1">
              Count
            </label>
            <input
              type="number"
              min={1}
              value={count}
              onChange={(e) => setCount(Number(e.target.value) || 1)}
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--accent))]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--foreground))] mb-1">
              Price (¢)
            </label>
            <input
              type="number"
              min={1}
              max={99}
              value={priceCents}
              onChange={(e) => setPriceCents(Number(e.target.value) || 50)}
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--accent))]"
            />
          </div>
        </div>

        {message && (
          <div
            className={status === "success"
              ? "rounded-lg bg-[hsl(var(--positive))]/20 text-[hsl(var(--positive))] px-4 py-2 text-sm"
              : "rounded-lg bg-red-500/20 text-red-400 px-4 py-2 text-sm"}
          >
            {message}
          </div>
        )}

        <button
          type="submit"
          disabled={status === "loading"}
          className="w-full rounded-lg bg-[hsl(var(--accent))] px-4 py-3 font-medium text-[hsl(220,18%,8%)] hover:opacity-90 disabled:opacity-50"
        >
          {status === "loading" ? "Placing…" : "Place limit order"}
        </button>
      </form>

      <p className="text-xs text-[hsl(var(--muted))]">
        Orders are sent to the backend; ensure KALSHI_API_KEY and KALSHI_PRIVATE_KEY are set in the
        backend .env for live trading.
      </p>
    </div>
  );
}
