import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from config import DATABASE_URL, DATABASE_POOL_SIZE, DATABASE_MAX_OVERFLOW

# Detect if using SQLite
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    # SQLite doesn't support connection pooling
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False} if "aiosqlite" in DATABASE_URL else {},
    )
else:
    # PostgreSQL with connection pooling
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=DATABASE_POOL_SIZE,
        max_overflow=DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for ORM models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI endpoints."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for non-endpoint usage."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
