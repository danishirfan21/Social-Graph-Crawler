import pytest

from app import database


@pytest.mark.asyncio
async def test_engine_factory_uses_queue_pool_for_postgresql(monkeypatch):
    monkeypatch.setattr(
        database.settings,
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/social_graph",
    )
    engine = database.create_database_engine()
    try:
        assert type(engine.pool).__name__ == "AsyncAdaptedQueuePool"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_engine_factory_accepts_sqlite_without_queue_options(monkeypatch):
    monkeypatch.setattr(database.settings, "DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = database.create_database_engine()
    try:
        async with engine.connect() as connection:
            await connection.exec_driver_sql("SELECT 1")
    finally:
        await engine.dispose()
