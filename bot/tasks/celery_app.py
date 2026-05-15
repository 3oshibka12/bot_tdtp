from celery import Celery
from celery.schedules import crontab
import asyncio
from db.database import async_session
from services.raitings import recalculate_all_ratings

app = Celery('dating_tasks', broker='amqp://guest:guest@rabbitmq:5672//')

# Настройка расписания
app.conf.beat_schedule = {
    'recalculate-every-hour': {
        'task': 'tasks.celery_app.recalculate_ratings',
        'schedule': crontab(minute='*'),
    },
}

@app.task
def recalculate_ratings():
    # Трюк для запуска асинхронного кода в синхронном Celery
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run_recalculate())

async def _run_recalculate():
    async with async_session() as session:
        await recalculate_all_ratings(session)