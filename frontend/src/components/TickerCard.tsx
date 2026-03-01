"use client";

import type { TickerSnapshot } from "@/lib/api";

export function TickerCard({ ticker }: { ticker: TickerSnapshot }) {
  const spread = ticker.yes_ask - ticker.yes_bid;
  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 hover:border-[hsl(var(--accent))]/40 transition-colors">
      <div className="font-mono text-sm font-semibold text-[hsl(var(--foreground))] mb-4 break-all">
        {ticker.market_ticker}
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-[hsl(var(--muted))] text-xs uppercase tracking-wider">Bid</div>
          <div className="text-lg font-semibold text-[hsl(var(--positive))]">{ticker.yes_bid}¢</div>
        </div>
        <div>
          <div className="text-[hsl(var(--muted))] text-xs uppercase tracking-wider">Ask</div>
          <div className="text-lg font-semibold text-[hsl(var(--negative))]">{ticker.yes_ask}¢</div>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-[hsl(var(--border))] text-xs text-[hsl(var(--muted))]">
        Spread: {spread}¢
      </div>
    </div>
  );
}
