"use client";

import type { NewsArticle } from "@/lib/api";
import { clsx } from "clsx";

export function NewsCard({ article }: { article: NewsArticle }) {
  const sentiment = article.sentiment;
  return (
    <article className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 hover:border-[hsl(var(--accent))]/40 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <a
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-[hsl(var(--foreground))] hover:text-[hsl(var(--accent))] line-clamp-2"
          >
            {article.headline}
          </a>
          {article.content_header && (
            <p className="text-sm text-[hsl(var(--muted))] mt-1 line-clamp-2">
              {article.content_header}
            </p>
          )}
          <p className="text-xs text-[hsl(var(--muted))] mt-2">
            {article.source} · {article.date}
          </p>
        </div>
        {sentiment && (
          <span
            className={clsx(
              "shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium uppercase",
              sentiment === "positive" && "bg-[hsl(var(--positive))]/20 text-[hsl(var(--positive))]",
              sentiment === "negative" && "bg-[hsl(var(--negative))]/20 text-[hsl(var(--negative))]",
              sentiment === "neutral" && "bg-[hsl(var(--neutral))]/20 text-[hsl(var(--neutral))]"
            )}
          >
            {sentiment}
          </span>
        )}
      </div>
    </article>
  );
}
