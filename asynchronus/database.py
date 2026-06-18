# from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession,async_sessionmaker,create_async_engine
# 1. Ensure this string starts with EXACTLY three slashes for a local relative file path
URL = "sqlite+aiosqlite:///async_my.db"

# 2. Safety Check: Only inject connect_args if we are actually loading a SQLite cluster instance
if URL.startswith("sqlite"):
    engine = create_async_engine(URL, connect_args={"check_same_thread": False})
else:
    # If you transition to PostgreSQL or MySQL later, they don't use check_same_threads
    engine = create_async_engine(URL)
#session=sessionmaker(bind=engine,autoflush=False,autocommit=False)
session=async_sessionmaker(engine,class_=AsyncSession,expire_on_commit=False)
class Base(DeclarativeBase):
    pass
# def get_db():
#     with session() as db:
#         yield db
async def get_db():
    async with session() as db:
        yield db