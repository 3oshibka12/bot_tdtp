import time
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from prometheus_client import Histogram, Counter

# Создаем метрики Прометеуса
REQUEST_TIME = Histogram('bot_request_processing_seconds', 'Time spent processing request')
REQUEST_COUNT = Counter('bot_requests_total', 'Total bot requests')

class MetricsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        REQUEST_COUNT.inc() # Увеличиваем счетчик запросов
        
        start_time = time.perf_counter()
        result = await handler(event, data)
        duration = time.perf_counter() - start_time
        
        REQUEST_TIME.observe(duration) # Записываем время выполнения
        
        return result