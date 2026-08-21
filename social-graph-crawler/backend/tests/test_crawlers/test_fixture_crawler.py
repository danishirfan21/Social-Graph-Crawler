import pytest
from sqlalchemy import select

from app.crawlers.fixture_crawler import FixtureCrawler
from app.models import CrawlJob, CrawlStatus, Edge, Node


@pytest.mark.asyncio
async def test_fixture_crawl_persists_normalized_graph(test_session):
    async with FixtureCrawler(test_session) as crawler:
        job = await crawler.crawl("Python", depth=2, max_entities=10)
    assert job.status == CrawlStatus.COMPLETED.value
    assert job.entity_count == 2
    assert len((await test_session.execute(select(Node))).scalars().all()) == 2
    assert len((await test_session.execute(select(Edge))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_fixture_repeated_crawl_does_not_duplicate_graph_records(test_session):
    async with FixtureCrawler(test_session) as crawler:
        await crawler.crawl("Python", depth=2, max_entities=10)
    async with FixtureCrawler(test_session) as crawler:
        await crawler.crawl("Python", depth=2, max_entities=10)
    assert len((await test_session.execute(select(Node))).scalars().all()) == 2
    assert len((await test_session.execute(select(Edge))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_fixture_failure_is_explicit(test_session):
    async with FixtureCrawler(test_session) as crawler:
        with pytest.raises(ValueError, match="instructed to fail"):
            await crawler.crawl("fail")

