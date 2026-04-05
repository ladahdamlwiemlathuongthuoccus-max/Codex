from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx
from bs4 import BeautifulSoup

from .base import BaseFetcher, RawArticle

logger = logging.getLogger(__name__)

USER_AGENT = (
    "AINewsBot/0.1 (Telegram AI Digest; +https://github.com/redpeak)"
)


class RSSFetcher(BaseFetcher):
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

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
        try:
            resp = await client.get(source["url"])
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch %s: %s", source["name"], e)
            return []

        feed = feedparser.parse(resp.text)
        articles = []

        for entry in feed.entries[:50]:
            title = entry.get("title", "").strip()
            if not title:
                continue

            url = entry.get("link", "")
            if not url:
                continue

            content = self._extract_content(entry)
            published = self._parse_date(entry)

            articles.append(RawArticle(
                url=url,
                title=title,
                content=content,
                published_at=published,
                source_name=source["name"],
                source_id=source["id"],
            ))

        logger.info("Fetched %d articles from %s", len(articles), source["name"])
        return articles

    def _extract_content(self, entry) -> str:
        content = ""

        if "content" in entry and entry.content:
            content = entry.content[0].get("value", "")
        elif "summary" in entry:
            content = entry.get("summary", "")
        elif "description" in entry:
            content = entry.get("description", "")

        if "<" in content:
            soup = BeautifulSoup(content, "lxml")
            content = soup.get_text(separator=" ", strip=True)

        return content[:5000]

    def _parse_date(self, entry) -> datetime | None:
        for field in ("published", "updated", "created"):
            val = entry.get(field)
            if val:
                try:
                    return parsedate_to_datetime(val)
                except Exception:
                    pass

            parsed = entry.get(f"{field}_parsed")
            if parsed:
                try:
                    from time import mktime
                    return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                except Exception:
                    pass

        return None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
