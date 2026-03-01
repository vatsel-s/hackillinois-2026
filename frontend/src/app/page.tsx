"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchNews, fetchTickers } from "@/lib/api";
import Link from "next/link";
import { Newspaper, TrendingUp, ArrowRight } from "lucide-react";

export default function DashboardPage() {
  const { data: news = [], isLoading: newsLoading, isError: newsError } = useQuery({
    queryKey: ["news", 10],
    queryFn: () => fetchNews(10),
  });
  const { data: tickers = [], isLoading: tickersLoading, isError: tickersError } = useQuery({
    queryKey: ["tickers"],
    queryFn: fetchTickers,
  });
  const backendDown = newsError || tickersError;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-[hsl(var(--muted))] mt-1">
          News-driven prediction market overview
        </p>
        {backendDown && (
          <div className="mt-3 rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-200 px-4 py-2 text-sm">
            Backend not reachable. Start it with: uvicorn backend.main:app --reload --port 8000
          </div>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[hsl(var(--accent))]" />
              Live Tickers
            </h2>
            <Link
              href="/markets"
              className="text-sm text-[hsl(var(--accent))] hover:underline flex items-center gap-1"
            >
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          {tickersLoading ? (
            <p className="text-[hsl(var(--muted))]">Loading tickers…</p>
          ) : tickers.length === 0 ? (
            <p className="text-[hsl(var(--muted))]">
              No tickers. Start the backend and add a watchlist.
            </p>
          ) : (
            <ul className="space-y-3">
              {tickers.slice(0, 5).map((t) => (
                <li
                  key={t.market_ticker}
                  className="flex justify-between items-center py-2 border-b border-[hsl(var(--border))] last:border-0"
                >
                  <span className="font-mono text-sm">{t.market_ticker}</span>
                  <span className="text-sm">
                    <span className="text-[hsl(var(--positive))]">{t.yes_bid}¢</span>
                    <span className="text-[hsl(var(--muted))] mx-1">/</span>
                    <span className="text-[hsl(var(--negative))]">{t.yes_ask}¢</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Newspaper className="w-5 h-5 text-[hsl(var(--accent))]" />
              Latest News
            </h2>
            <Link
              href="/news"
              className="text-sm text-[hsl(var(--accent))] hover:underline flex items-center gap-1"
            >
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          {newsLoading ? (
            <p className="text-[hsl(var(--muted))]">Loading news…</p>
          ) : news.length === 0 ? (
            <p className="text-[hsl(var(--muted))]">
              No articles. Start the backend and RSS pipeline.
            </p>
          ) : (
            <ul className="space-y-3">
              {news.slice(0, 5).map((a) => (
                <li key={a.link} className="border-b border-[hsl(var(--border))] last:border-0 pb-3">
                  <a
                    href={a.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-sm hover:text-[hsl(var(--accent))] line-clamp-2"
                  >
                    {a.headline}
                  </a>
                  <p className="text-xs text-[hsl(var(--muted))] mt-0.5">
                    {a.source} · {a.date}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6">
        <h2 className="text-lg font-semibold mb-2">Quick actions</h2>
        <div className="flex flex-wrap gap-4">
          <Link
            href="/markets"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--accent))]/20 text-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/30"
          >
            <TrendingUp className="w-4 h-4" /> Watch markets
          </Link>
          <Link
            href="/orders"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--accent))]/20 text-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/30"
          >
            Place order
          </Link>
          <Link
            href="/news"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--surface-muted))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--border))]"
          >
            <Newspaper className="w-4 h-4" /> Browse news
          </Link>
        </div>
      </div>
    </div>
  );
}
