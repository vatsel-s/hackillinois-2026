"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchNews } from "@/lib/api";
import { NewsCard } from "@/components/NewsCard";

export default function NewsPage() {
  const { data: articles = [], isLoading, error } = useQuery({
    queryKey: ["news", 50],
    queryFn: () => fetchNews(50),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">News Feed</h1>
        <p className="text-[hsl(var(--muted))] mt-1">
          Headlines from RSS pipeline; sentiment from backend when available
        </p>
      </div>

      {isLoading && (
        <p className="text-[hsl(var(--muted))]">Loading news…</p>
      )}
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3">
          Failed to load news. Is the backend running on port 8000?
        </div>
      )}
      {!isLoading && !error && articles.length === 0 && (
        <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-8 text-center text-[hsl(var(--muted))]">
          No articles yet. Run the RSS pipeline to ingest news.
        </div>
      )}

      <div className="space-y-4">
        {articles.map((a) => (
          <NewsCard key={a.link} article={a} />
        ))}
      </div>
    </div>
  );
}
