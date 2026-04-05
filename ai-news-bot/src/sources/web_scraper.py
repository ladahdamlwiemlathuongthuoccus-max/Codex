from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from .base import BaseFetcher, RawArticle

logger = logging.getLogger(__name__)

USER_AGENT = (
    "AINewsBot/0.1 (Telegram AI Digest; +https://github.com/redpeak)"
)

# Scraping configs for known sites
SCRAPER_CONFIGS = {
    "The Batch": {
        "article_selector": "article, .post-card, .batch-article",
        "title_selector": "h2, h3, .post-card__title",
        "link_selector": "a",
        "base_url": "https://www.deeplearning.ai",
    },
}


class WebScraperFetcher(BaseFetcher):
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
        return self._client

    async def fetch(self, source: dict) -> list[RawArticle]:
        client = await self._get_client()
        config = SCRAPER_CONFIGS.get(source["name"], {})

        try:
            resp = await client.get(source["url"])
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Failed to scrape %s: %s", source["name"], e)
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        articles = []

        article_selector = config.get("article_selector", "article")
        title_selector = config.get("title_selector", "h2, h3")
        link_selector = config.get("link_selector", "a")
        base_url = config.get("base_url", "")

        for el in soup.select(article_selector)[:20]:
            title_el = el.select_one(title_selector)
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            link_el = el.select_one(link_selector)
            url = ""
            if link_el and link_el.get("href"):
                url = link_el["href"]
                if url.startswith("/"):
                    url = base_url + url

            content = el.get_text(separator=" ", strip=True)[:3000]

            articles.append(RawArticle(
                url=url or source["url"],
                title=title,
                content=content,
                published_at=datetime.now(timezone.utc),
                source_name=source["name"],
                source_id=source["id"],
            ))

        logger.info("Scraped %d articles from %s", len(articles), source["name"])
        return articles

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
