"""Deterministic source used to exercise the complete ingestion pipeline locally."""

from uuid import uuid4

from app.crawlers.base import BaseCrawler
from app.models import CrawlJob, CrawlStatus


class FixtureCrawler(BaseCrawler):
    """A credential-free, deterministic graph source for development and tests."""

    def get_source_name(self) -> str:
        return "fixture"

    async def crawl(self, start_entity: str, depth: int = 2, max_entities: int = 100, job: CrawlJob | None = None) -> CrawlJob:
        if start_entity == "fail":
            raise ValueError("fixture source was instructed to fail")
        if job is None:
            job = await self.create_crawl_job(start_entity, f"direct:{start_entity}:{uuid4()}")
        await self.update_crawl_job(job, CrawlStatus.RUNNING)
        root = await self.create_or_update_node("topic", start_entity.lower(), start_entity, {"kind": "fixture"})
        if depth > 1 and max_entities > 1:
            child = await self.create_or_update_node("person", f"{start_entity.lower()}-author", "Fixture Author", {"kind": "fixture"})
            await self.create_edge(child, root, "mentions", 1.0, {"fixture": True})
        await self.update_crawl_job(job, CrawlStatus.COMPLETED, len(self.discovered_nodes), len(self.discovered_edges))
        await self.db.commit()
        return job
