import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app import config
from app.database.db import init_db
from app.handlers.commands import router as commands_router
from app.handlers.admin import router as admin_router
from app.handlers.group import router as group_router


async def main():
    if not config.BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN kiritilmagan. .env faylini tekshiring."
        )

    logging.basicConfig(level=logging.INFO)

    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(commands_router)
    dp.include_router(admin_router)
    dp.include_router(group_router)

    logging.info("RoastAI Group Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
