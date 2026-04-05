from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ...storage.database import Database
from ...storage import queries

logger = logging.getLogger(__name__)

router = Router()


class AdminFilter:
    def __init__(self, admin_id: int):
        self._admin_id = admin_id

    async def __call__(self, message: Message) -> bool:
        return message.from_user and message.from_user.id == self._admin_id


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database, admin_id: int) -> None:
    if message.from_user.id != admin_id:
        await message.answer("Доступ только для администратора.")
        return

    stats = await queries.get_stats(db)

    text = (
        "<b>Статистика бота:</b>\n\n"
        f"Статей всего: {stats['total_articles']}\n"
        f"Обработано: {stats['processed_articles']}\n"
        f"Подписчиков: {stats['active_subscribers']}\n"
        f"Источников: {stats['active_sources']}\n"
        f"С ошибками: {stats['sources_with_errors']}"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("force_fetch"))
async def cmd_force_fetch(message: Message, db: Database, admin_id: int, pipeline=None) -> None:
    if message.from_user.id != admin_id:
        await message.answer("Доступ только для администратора.")
        return

    if pipeline is None:
        await message.answer("Pipeline не инициализирован.")
        return

    await message.answer("Запускаю принудительный цикл сбора...")

    try:
        result = await pipeline.run_fetch_cycle()
        text = (
            f"Цикл завершен:\n"
            f"Собрано: {result['fetched']}\n"
            f"Новых: {result['new']}\n"
            f"Дубликатов: {result['duplicates']}\n"
            f"Обработано LLM: {result['processed']}\n"
            f"Ошибок: {result['errors']}"
        )
    except Exception as e:
        logger.error("Force fetch error: %s", e)
        text = f"Ошибка: {e}"

    await message.answer(text)
