from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawArticle:
    url: str
    title: str
    content: str
    published_at: datetime | None
    source_name: str
    source_id: int


class BaseFetcher(ABC):
    @abstractmethod
    async def fetch(self, source: dict) -> list[RawArticle]:
        ...
