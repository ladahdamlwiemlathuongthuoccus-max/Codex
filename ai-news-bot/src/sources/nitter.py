from __future__ import annotations

import logging

import httpx

from .rss import RSSFetcher
from .base import RawArticle

logger = logging.getLogger(__name__)

NITTER_MIRRORS = [
    "nitter.net",
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.1d4.us",
    "nitter.kavin.rocks",
]


class NitterFetcher(RSSFetcher):
    async def fetch(self, source: dict) -> list[RawArticle]:
        original_url = source["url"]

        for mirror in NITTER_MIRRORS:
            url = self._replace_mirror(original_url, mirror)
            source_copy = {**source, "url": url}

            try:
                articles = await super().fetch(source_copy)
                if articles:
                    logger.info("Nitter mirror %s works for %s", mirror, source["name"])
                    # Convert nitter URLs to official x.com URLs
                    for article in articles:
                        article.url = self._to_official_url(article.url)
                    return articles
            except Exception as e:
                logger.debug("Nitter mirror %s failed for %s: %s", mirror, source["name"], e)
                continue

        logger.warning("All Nitter mirrors failed for %s", source["name"])
        return []

    def _replace_mirror(self, url: str, mirror: str) -> str:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        return urlunparse(parsed._replace(netloc=mirror))

    @staticmethod
    def _to_official_url(url: str) -> str:
        """Convert nitter mirror URLs to official x.com URLs."""
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        for mirror in NITTER_MIRRORS:
            if mirror in hostname:
                clean = urlunparse(parsed._replace(
                    scheme="https",
                    netloc="x.com",
                    fragment="",
                ))
                return clean
        return url
