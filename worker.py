import asyncio
import logging
from database import async_session, init_db
from crud import recalculate_all_ratings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Воркер запускается...")
    # Инициализируем БД (создаем таблицы если их нет)
    await init_db()
    
    while True:
        try:
            logger.info("🔄 Начинаю плановый пересчет рейтингов всех пользователей...")
            async with async_session() as session:
                await recalculate_all_ratings(session)
            logger.info("✅ Пересчет успешно завершен. Жду 1 час.")
        except Exception as e:
            logger.error(f"❌ Ошибка в воркере: {e}")
        
        await asyncio.sleep(3600)  # Раз в час

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Воркер остановлен")