from sqlalchemy import Column, BigInteger, String, Integer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

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

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("База данных инициализирована")