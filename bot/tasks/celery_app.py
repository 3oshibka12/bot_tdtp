from celery import Celery
from celery.schedules import crontab
import asyncio
from db.database import async_session
from services.raitings import recalculate_all_ratings
from aiogram.client.default import DefaultBotProperties


app = Celery('dating_tasks', broker='amqp://guest:guest@rabbitmq:5672//')

# Настройка расписания
app.conf.beat_schedule = {
    'recalculate-every-hour': {
        'task': 'tasks.celery_app.recalculate_ratings',
        'schedule': crontab(minute='*'),
    },
    'send-retention-push': {
        'task': 'tasks.celery_app.send_notifications',
        'schedule': crontab(minute='*/2'),
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


from aiogram import Bot
from sqlalchemy import select

BOT_TOKEN = "8602804233:AAFAL5k937tZNe3tYI58zC89uSBp4dOGf4A"

@app.task
def send_notifications():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run_notifications())

async def _run_notifications():
    from db.database import async_session, User
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        users = result.scalars().all()
        
        for user_id in users:
            try:
                await bot.send_message(
                    user_id, 
                    "🔔 <b>Эй!</b> Давно не виделись!\nЗаходи в бота, там могут быть новые анкеты и мэтчи!"
                )
            except Exception as e:
                pass
                
    await bot.session.close()