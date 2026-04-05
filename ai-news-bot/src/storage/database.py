from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

from .models import SCHEMA_SQL, SCHEMA_VERSION

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    @classmethod
    async def create(cls, db_path: str | Path) -> Database:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db = cls(db_path)
        await db._connect()
        await db._run_migrations()
        return db

    async def _connect(self) -> None:
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")

    async def _run_migrations(self) -> None:
        assert self._conn is not None
        await self._conn.executescript(SCHEMA_SQL)

        cursor = await self._conn.execute(
            "SELECT MAX(version) as v FROM schema_version"
        )
        row = await cursor.fetchone()
        current = row["v"] if row and row["v"] else 0

        if current < 2:
            try:
                await self._conn.execute("ALTER TABLE articles ADD COLUMN title_ru TEXT")
            except Exception:
                pass  # column already exists

        if current < 3:
            try:
                await self._conn.execute(
                    "ALTER TABLE subscribers ADD COLUMN instant_count_today INTEGER DEFAULT 0"
                )
            except Exception:
                pass  # column already exists

        if current < SCHEMA_VERSION:
            await self._conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            await self._conn.commit()
            logger.info("Database migrated to version %d", SCHEMA_VERSION)

    @property
    def conn(self) -> aiosqlite.Connection:
        assert self._conn is not None, "Database not connected"
        return self._conn

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
