from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from .config.settings import EnvSettings, load_yaml_config
from .storage.database import Database
from .storage.queries import sync_sources
from .processing.llm import LLMProcessor
from .processing.pipeline import Pipeline
from .bot.app import create_dispatcher
from .bot.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent.parent / "data" / "logs" / "bot.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # Load config
    env = EnvSettings()
    config = load_yaml_config()
    logger.info("Config loaded: %d sources, %d tags", len(config.sources), len(config.tags))

    # Initialize database
    db_path = Path(__file__).parent.parent / "data" / "news.db"
    db = await Database.create(db_path)
    await sync_sources(db, config.sources)
    logger.info("Database ready")

    # Initialize LLM
    llm = LLMProcessor(
        api_key=env.openrouter_api_key,
        summarize_model=config.llm.summarize_model,
        digest_model=config.llm.digest_model,
    )

    # Initialize pipeline
    pipeline = Pipeline(db=db, llm=llm, config=config)

    # Create bot
    bot = Bot(
        token=env.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    # Create dispatcher with dependency injection
    dp = create_dispatcher()

    # Start scheduler
    scheduler = setup_scheduler(
        db=db, bot=bot, pipeline=pipeline, llm=llm, config=config,
    )
    scheduler.start()
    logger.info("Scheduler started")

    # Start polling
    try:
        logger.info("Bot starting polling...")
        await dp.start_polling(
            bot,
            db=db,
            admin_id=env.admin_telegram_id,
            pipeline=pipeline,
        )
    finally:
        scheduler.shutdown(wait=False)
        await pipeline.close()
        await db.close()
        await bot.session.close()
        logger.info("Bot stopped")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
