from __future__ import annotations

from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ...storage.database import Database
from ...storage import queries
from ..formatter import format_digest

router = Router()


@router.message(Command("digest"))
async def cmd_digest(message: Message, db: Database) -> None:
    articles = await queries.get_digest_articles(db, hours=24, limit=20)

    if not articles:
        await message.answer("Пока нет обработанных новостей. Попробуйте позже.")
        return

    date_str = datetime.now().strftime("%d %B %Y")
    messages = format_digest(articles, date_str)

    for msg in messages:
        await message.answer(msg, parse_mode="HTML", disable_web_page_preview=True)
