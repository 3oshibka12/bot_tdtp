from sqlalchemy import Column, BigInteger, String, Integer, DateTime, func, ForeignKey, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Используем localhost и порт 5433 (который проброшен из Docker)
DB_URL = "postgresql+asyncpg://dating:dating123@localhost:5433/dating_bot"

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    telegram_id = Column(BigInteger, primary_key=True)
    full_name = Column(String(255))
    age = Column(Integer)
    gender = Column(String(10))
    city = Column(String(100))
    bio = Column(String)
    
    # Уровень 1: Первичный рейтинг
    profile_completeness = Column(Float, default=0.0)
    photo_count = Column(Integer, default=0)
    
    # Уровень 2: Поведенческий рейтинг
    likes_received = Column(Integer, default=0)
    dislikes_received = Column(Integer, default=0)
    match_count = Column(Integer, default=0)
    
    # Уровень 3: Итоговый рейтинг
    rating = Column(Float, default=5.0)
    
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Interaction(Base):
    __tablename__ = 'interactions'

    id = Column(Integer, primary_key=True)
    initiator_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    target_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    action = Column(String(10))
    timestamp = Column(DateTime, server_default=func.now())


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных инициализирована")