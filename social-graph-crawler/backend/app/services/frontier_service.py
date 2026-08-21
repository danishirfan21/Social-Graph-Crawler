"""PostgreSQL-backed frontier claiming and terminal job state calculation."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import logging

from sqlalchemy import exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import CrawlFrontierItem, CrawlJob, CrawlStatus, FrontierStatus

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def add_frontier_item(db: AsyncSession, job_id: UUID, source: str, target: str, depth: int = 1) -> UUID | None:
    try:
        async with db.begin_nested():
            item = CrawlFrontierItem(crawl_job_id=job_id, source=source, target=target, depth=depth)
            db.add(item)
            await db.flush()
        return item.id
    except Exception:
        return False


async def recover_stale_items(db: AsyncSession, job_id: UUID | None = None) -> int:
    statement = update(CrawlFrontierItem).where(
        CrawlFrontierItem.status == FrontierStatus.PROCESSING.value,
        CrawlFrontierItem.lease_expires_at < utcnow(),
    ).values(status=FrontierStatus.QUEUED.value, worker_id=None, lease_expires_at=None)
    if job_id:
        statement = statement.where(CrawlFrontierItem.crawl_job_id == job_id)
    result = await db.execute(statement)
    return result.rowcount or 0


async def claim_item(db: AsyncSession, job_id: UUID, worker_id: str, frontier_id: UUID | None = None) -> CrawlFrontierItem | None:
    await recover_stale_items(db, job_id)
    statement = select(CrawlFrontierItem).where(CrawlFrontierItem.crawl_job_id == job_id, CrawlFrontierItem.status == FrontierStatus.QUEUED.value)
    if frontier_id:
        statement = statement.where(CrawlFrontierItem.id == frontier_id)
    result = await db.execute(
        statement
        .order_by(CrawlFrontierItem.discovered_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    item = result.scalar_one_or_none()
    if item is None:
        return None
    now = utcnow()
    item.status = FrontierStatus.PROCESSING.value
    item.worker_id = worker_id
    item.processing_at = now
    item.lease_expires_at = now + timedelta(seconds=settings.FRONTIER_LEASE_SECONDS)
    item.attempt_count += 1
    await db.flush()
    return item


async def refresh_job_status(db: AsyncSession, job_id: UUID) -> None:
    """Finalize only when PostgreSQL sees no queued/processing frontier rows.

    Every worker may call this. The conditional UPDATE makes repeated/racing
    calls harmless and avoids deriving parent state from process-local counts.
    """
    await db.flush()
    counts = dict((await db.execute(select(CrawlFrontierItem.status, func.count()).where(CrawlFrontierItem.crawl_job_id == job_id).group_by(CrawlFrontierItem.status))).all())
    non_terminal = exists(select(CrawlFrontierItem.id).where(
        CrawlFrontierItem.crawl_job_id == job_id,
        CrawlFrontierItem.status.in_([FrontierStatus.QUEUED.value, FrontierStatus.PROCESSING.value]),
    ))
    has_items = exists(select(CrawlFrontierItem.id).where(CrawlFrontierItem.crawl_job_id == job_id))
    completed_count = counts.get(FrontierStatus.COMPLETED.value, 0)
    failed_count = counts.get(FrontierStatus.FAILED.value, 0)
    result = await db.execute(
        update(CrawlJob)
        .where(CrawlJob.id == job_id, CrawlJob.status.in_([CrawlStatus.PENDING.value, CrawlStatus.RUNNING.value]), has_items, ~non_terminal)
        .values(
            status=CrawlStatus.COMPLETED.value,
            entity_count=completed_count,
            completed_at=utcnow(),
            error_message=(f"{failed_count} frontier item(s) failed" if failed_count else None),
        )
    )
    logger.info("crawl.finalization_checked crawl_job_id=%s frontier_counts=%s finalized=%s", job_id, counts, result.rowcount)


async def frontier_counts(db: AsyncSession, job_id: UUID) -> dict[str, int]:
    rows = (await db.execute(select(CrawlFrontierItem.status, func.count()).where(CrawlFrontierItem.crawl_job_id == job_id).group_by(CrawlFrontierItem.status))).all()
    return {status: count for status, count in rows}
