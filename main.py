import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from aiogram.client.session.aiohttp import AiohttpSession

from database import init_db
from handlers import router


BOT_TOKEN = "8602804233:AAFAL5k937tZNe3tYI58zC89uSBp4dOGf4A"
REDIS_URL = "redis://localhost:6379/0"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    # 1. Создаем таблицы в БД
    await init_db()
    
    # 2. Подключаем Redis для состояний
    redis = Redis.from_url(REDIS_URL)
    storage = RedisStorage(redis)
    
    # 3. Инициализируем бота
    session = AiohttpSession(
        timeout=8.,
        proxy='http://109.107.179.140:8090',
    )
    
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher(storage=storage)
    
    # 4. Подключаем все хэндлеры из файла handlers.py
    dp.include_router(router)
    
    print("🤖 Бот запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis.close()

if __name__ == "__main__":
    asyncio.run(main())