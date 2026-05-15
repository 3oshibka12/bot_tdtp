import time
import logging
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class MetricsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        start_time = time.perf_counter() # Засекаем время
        
        result = await handler(event, data) # Пропускаем запрос дальше
        
        duration = (time.perf_counter() - start_time) * 1000 # В миллисекундах
        user_id = data.get("event_from_user").id if data.get("event_from_user") else "Unknown"
        
        logging.info(f"📊 [МЕТРИКА] Запрос пользователя {user_id} обработан за {duration:.2f} мс")
        return result