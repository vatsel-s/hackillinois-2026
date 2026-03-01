"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchTickers } from "@/lib/api";
import { TickerCard } from "@/components/TickerCard";

export default function MarketsPage() {
  const { data: tickers = [], isLoading, error } = useQuery({
    queryKey: ["tickers"],
    queryFn: fetchTickers,
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Markets</h1>
        <p className="text-[hsl(var(--muted))] mt-1">
          Live bid/ask from your watchlist (updates every 5s; backend can add WebSocket)
        </p>
      </div>

      {isLoading && (
        <p className="text-[hsl(var(--muted))]">Loading tickers…</p>
      )}
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3">
          Failed to load tickers. Is the backend running on port 8000?
        </div>
      )}
      {!isLoading && !error && tickers.length === 0 && (
        <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-8 text-center text-[hsl(var(--muted))]">
          No tickers in watchlist. Configure watchlist in the backend.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tickers.map((t) => (
          <TickerCard key={t.market_ticker} ticker={t} />
        ))}
      </div>
    </div>
  );
}
