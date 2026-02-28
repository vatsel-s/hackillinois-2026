"""
nlp/article_fetcher.py — Async full-article text fetcher.

Fetches full article text for Stage 2 (FinBERT) deep scoring.
Uses newspaper3k for content extraction (handles most news sites cleanly).
Falls back to raw HTML scraping if newspaper3k fails.
"""

import asyncio
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger("article_fetcher")

# Sites that block scrapers — skip full-text fetch for these
BLOCKED_DOMAINS = {
    "wsj.com", "ft.com", "bloomberg.com",
    "nytimes.com", "washingtonpost.com",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


async def fetch_article_text(url: str, client: httpx.AsyncClient) -> Optional[str]:
    """
    Fetch and extract the main article text from a URL.
    Returns None if fetch fails or domain is blocked.
    """
    if not url or url.startswith("https://reddit.com"):
        return None

    domain = _extract_domain(url)
    if any(blocked in domain for blocked in BLOCKED_DOMAINS):
        logger.debug(f"Skipping paywalled domain: {domain}")
        return None

    try:
        response = await client.get(url, headers=_HEADERS, timeout=10)
        if response.status_code != 200:
            return None

        html = response.text

        # Try newspaper3k extraction (best quality)
        text = _extract_with_newspaper(url, html)
        if text and len(text) > 100:
            return text[:3000]  # cap to avoid huge texts

        # Fallback: strip tags and get readable text
        text = _extract_fallback(html)
        return text[:3000] if text and len(text) > 100 else None

    except Exception as e:
        logger.debug(f"Article fetch failed ({url[:50]}): {e}")
        return None


def _extract_with_newspaper(url: str, html: str) -> Optional[str]:
    """Use newspaper3k for high-quality article extraction."""
    try:
        from newspaper import Article
        article = Article(url)
        article.set_html(html)
        article.parse()
        return article.text
    except ImportError:
        logger.debug("newspaper3k not installed — using fallback extractor")
        return None
    except Exception:
        return None


def _extract_fallback(html: str) -> str:
    """Strip HTML tags and return clean text."""
    # Remove scripts, styles, and tags
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html)
    # Remove common boilerplate patterns
    html = re.sub(r"(cookie|privacy policy|sign up|subscribe).{0,100}", "", html, flags=re.IGNORECASE)
    return html.strip()


def _extract_domain(url: str) -> str:
    try:
        return url.split("/")[2].lower().lstrip("www.")
    except Exception:
        return ""