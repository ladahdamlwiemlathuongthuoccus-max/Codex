from __future__ import annotations

import json
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from ..config.settings import AppConfig
from ..processing.pipeline import Pipeline
from ..processing.llm import LLMProcessor
from ..processing.prompts import SYSTEM_PROMPT_DIGEST
from ..storage.database import Database
from ..storage import queries
from .formatter import format_digest, format_instant

logger = logging.getLogger(__name__)


def setup_scheduler(
    db: Database,
    bot: Bot,
    pipeline: Pipeline,
    llm: LLMProcessor,
    config: AppConfig,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=config.bot.timezone)

    # Fetch cycle
    scheduler.add_job(
        _fetch_and_dispatch,
        "interval",
        minutes=config.bot.fetch_interval_minutes,
        id="fetch_cycle",
        kwargs={"db": db, "bot": bot, "pipeline": pipeline, "config": config},
    )

    # Daily digest
    hour, minute = map(int, config.bot.digest_time.split(":"))
    scheduler.add_job(
        _send_daily_digest,
        "cron",
        hour=hour,
        minute=minute,
        id="daily_digest",
        kwargs={"db": db, "bot": bot, "llm": llm, "config": config},
    )

    # Cleanup old articles
    scheduler.add_job(
        _cleanup,
        "cron",
        hour=3,
        minute=0,
        id="cleanup",
        kwargs={"db": db},
    )

    # Reset daily LLM counter at midnight
    scheduler.add_job(
        _reset_counters,
        "cron",
        hour=0,
        minute=0,
        id="reset_counters",
        kwargs={"llm": llm, "db": db},
    )

    return scheduler


async def _fetch_and_dispatch(
    db: Database,
    bot: Bot,
    pipeline: Pipeline,
    config: AppConfig,
) -> None:
    try:
        result = await pipeline.run_fetch_cycle()
        logger.info("Fetch cycle completed: %s", result)

        # Dispatch instant notifications (respecting daily limit)
        threshold = config.bot.instant_threshold
        max_instant = config.bot.max_instant_per_day
        urgent = await queries.get_unsent_instant(db, threshold)

        if urgent:
            # Track sent count per subscriber in memory to enforce limit
            sent_count: dict[int, int] = {}
            subscribers = await queries.get_instant_subscribers(db, max_per_day=max_instant)
            for sub in subscribers:
                sent_count[sub["telegram_id"]] = sub.get("instant_count_today", 0)

            for article in urgent:
                text = format_instant(article)
                for sub in subscribers:
                    tid = sub["telegram_id"]
                    if sent_count.get(tid, 0) >= max_instant:
                        continue
                    if _matches_filter(article, sub):
                        try:
                            await bot.send_message(
                                tid,
                                text,
                                parse_mode="HTML",
                                disable_web_page_preview=True,
                            )
                            sent_count[tid] = sent_count.get(tid, 0) + 1
                            await queries.increment_instant_count(db, tid)
                        except Exception as e:
                            logger.warning("Failed to send to %s: %s", tid, e)
                await queries.mark_sent_instant(db, article["id"])

    except Exception as e:
        logger.error("Fetch and dispatch error: %s", e)


async def _send_daily_digest(
    db: Database,
    bot: Bot,
    llm: LLMProcessor,
    config: AppConfig,
) -> None:
    try:
        articles = await queries.get_digest_articles(
            db, hours=24, limit=config.bot.max_articles_per_digest,
        )

        if not articles:
            logger.info("No articles for daily digest")
            return

        date_str = datetime.now().strftime("%d %B %Y")
        messages = format_digest(articles, date_str)

        subscribers = await queries.get_digest_subscribers(db)
        for sub in subscribers:
            for msg in messages:
                try:
                    await bot.send_message(
                        sub["telegram_id"],
                        msg,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception as e:
                    logger.warning("Failed to send digest to %s: %s", sub["telegram_id"], e)

        article_ids = [a["id"] for a in articles]
        await queries.mark_sent_digest(db, article_ids)
        logger.info("Daily digest sent to %d subscribers (%d articles)", len(subscribers), len(articles))

    except Exception as e:
        logger.error("Daily digest error: %s", e)


async def _cleanup(db: Database) -> None:
    try:
        deleted = await queries.cleanup_old_articles(db, days=30)
        if deleted:
            logger.info("Cleaned up %d old articles", deleted)
    except Exception as e:
        logger.error("Cleanup error: %s", e)


async def _reset_counters(llm: LLMProcessor, db: Database) -> None:
    llm.reset_daily_counter()
    await queries.reset_instant_counts(db)
    logger.info("Daily LLM and instant counters reset")


def _matches_filter(article: dict, subscriber: dict) -> bool:
    tag_filter = subscriber.get("tag_filter")
    if not tag_filter:
        return True

    if isinstance(tag_filter, str):
        try:
            tag_filter = json.loads(tag_filter)
        except (json.JSONDecodeError, TypeError):
            return True

    if not tag_filter:
        return True

    article_tags = article.get("tags", "[]")
    if isinstance(article_tags, str):
        try:
            article_tags = json.loads(article_tags)
        except (json.JSONDecodeError, TypeError):
            article_tags = []

    return bool(set(article_tags) & set(tag_filter))
