import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from aiogram.client.session.aiohttp import AiohttpSession

from database import init_db
from handlers import router
from aiogram.client.default import DefaultBotProperties


BOT_TOKEN = "8602804233:AAFAL5k937tZNe3tYI58zC89uSBp4dOGf4A"
REDIS_URL = "redis://localhost:6379/0"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    
    
    await init_db()
    
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True) # decode_responses=True важен для работы с ключами-строками
    storage = RedisStorage(redis_client)
    
    # Убираем прокси, если он не нужен. Если нужен, верните его.
    session = AiohttpSession(
        timeout=8.,
        proxy='http://109.107.179.140:8090',
    )
    
    bot = Bot(
        token=BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    # Передаем redis и bot в хендлеры через аргументы диспетчера
    dp = Dispatcher(storage=storage, redis=redis_client, bot=bot)
    
    dp.include_router(router)
    
    print("🤖 Бот запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())