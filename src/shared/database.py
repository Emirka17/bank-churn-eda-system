from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.shared.config import settings

# Создаем асинхронный движок
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Создаем фабрику сессий (через них мы будем делать запросы)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Базовый класс для всех наших будущих таблиц
Base = declarative_base()
