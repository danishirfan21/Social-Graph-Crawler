"""ARQ worker for durable V2 fixture frontier processing."""
import asyncio
import logging
import os
from datetime import timedelta
from time import monotonic
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings
from app.database import AsyncSessionLocal, close_db
from app.models import CrawlFrontierItem, CrawlJob, CrawlStatus, Edge, FrontierStatus, Node
from sqlalchemy import select
from app.services.frontier_service import claim_item, refresh_job_status, utcnow
from app.services.metrics import frontier_completed, frontier_failed, frontier_retries, processing_seconds, worker_tasks

logger = logging.getLogger(__name__)


class TransientFixtureError(Exception):
    pass


async def throttle(redis, source: str) -> None:
    """Cross-worker source-level spacing; fixed config is enough for the demo."""
    interval_ms = max(1, int(1000 / settings.FIXTURE_REQUESTS_PER_SECOND))
    key = f"crawl:throttle:{source}"
    while not await redis.set(key, "1", nx=True, px=interval_ms):
        await asyncio.sleep(interval_ms / 1000)


async def persist_fixture(db, job: CrawlJob, item: CrawlFrontierItem) -> None:
    """Deterministic fixture cases: success, transient, permanent, duplicate, slow."""
    target = item.target
    if target == "slow":
        await asyncio.sleep(2)
    if target == "transient" and item.attempt_count < 3:
        raise TransientFixtureError("deterministic transient fixture failure")
    if target == "permanent":
        raise ValueError("deterministic permanent fixture failure")
    root_id = f"{job.start_entity.lower()}-{target}"
    root = (await db.execute(select(Node).where(Node.source == "fixture", Node.entity_type == "topic", Node.entity_id == root_id))).scalar_one_or_none()
    if root is None:
        root = Node(source="fixture", entity_type="topic", entity_id=root_id, display_name=target, data={"fixture_case": target})
        db.add(root)
        await db.flush()
    child_id = f"{root_id}-author"
    child = (await db.execute(select(Node).where(Node.source == "fixture", Node.entity_type == "person", Node.entity_id == child_id))).scalar_one_or_none()
    if child is None:
        child = Node(source="fixture", entity_type="person", entity_id=child_id, display_name=f"{target} author", data={"fixture_case": target})
        db.add(child)
        await db.flush()
    edge = (await db.execute(select(Edge).where(Edge.source_node_id == child.id, Edge.target_node_id == root.id, Edge.relationship_type == "mentions"))).scalar_one_or_none()
    if edge is None:
        db.add(Edge(source_node_id=child.id, target_node_id=root.id, relationship_type="mentions", weight=1.0, data={"fixture": True}))


async def process_frontier_item(ctx, job_id: str, frontier_item_id: str) -> None:
    worker_id = os.getenv("HOSTNAME", "worker")
    async with AsyncSessionLocal() as db:
        job_uuid = UUID(job_id)
        item = await claim_item(db, job_uuid, worker_id, UUID(frontier_item_id))
        if item is None:
            logger.info("frontier.not_claimed crawl_job_id=%s frontier_item_id=%s worker_id=%s", job_id, frontier_item_id, worker_id)
            await refresh_job_status(db, job_uuid)
            await db.commit()
            return
        await db.commit()
        logger.info("frontier.claimed crawl_job_id=%s frontier_item_id=%s target=%s worker_id=%s attempt=%s", job_id, item.id, item.target, worker_id, item.attempt_count)
        started = monotonic()
        try:
            await throttle(ctx["redis"], item.source)
            job = await db.get(CrawlJob, job_uuid)
            await persist_fixture(db, job, item)
            item.status, item.completed_at, item.lease_expires_at = FrontierStatus.COMPLETED.value, utcnow(), None
            frontier_completed.inc()
            worker_tasks.labels("completed").inc()
            logger.info("frontier.completed crawl_job_id=%s frontier_item_id=%s worker_id=%s", job_id, item.id, worker_id)
        except TransientFixtureError as exc:
            item.last_error, item.lease_expires_at, item.worker_id = str(exc), None, None
            if item.attempt_count >= settings.FRONTIER_MAX_ATTEMPTS:
                item.status, item.completed_at = FrontierStatus.FAILED.value, utcnow()
                frontier_failed.inc()
                worker_tasks.labels("failed").inc()
            else:
                item.status = FrontierStatus.QUEUED.value
                frontier_retries.inc()
                worker_tasks.labels("retry").inc()
                await ctx["redis"].enqueue_job("process_frontier_item", job_id, str(item.id), _defer_by=timedelta(seconds=0.1 * 2 ** (item.attempt_count - 1)))
                logger.info("frontier.retry crawl_job_id=%s frontier_item_id=%s attempt=%s", job_id, item.id, item.attempt_count)
        except Exception as exc:
            item.status, item.last_error, item.completed_at, item.lease_expires_at = FrontierStatus.FAILED.value, str(exc)[:2000], utcnow(), None
            frontier_failed.inc()
            worker_tasks.labels("failed").inc()
            logger.info("frontier.failed crawl_job_id=%s frontier_item_id=%s error=%s", job_id, item.id, exc)
        finally:
            processing_seconds.observe(monotonic() - started)
            await refresh_job_status(db, job_uuid)
            await db.commit()


async def startup(ctx):
    ctx["redis"] = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))


async def shutdown(ctx):
    await ctx["redis"].aclose()
    await close_db()


class WorkerSettings:
    functions = [process_frontier_item]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
