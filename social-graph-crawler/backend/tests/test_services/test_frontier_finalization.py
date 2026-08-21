from sqlalchemy import select

from app.models import CrawlFrontierItem, CrawlJob, CrawlStatus, FrontierStatus
from app.services.frontier_service import refresh_job_status, utcnow


async def test_finalization_waits_for_non_terminal_items_and_is_idempotent(test_session):
    job = CrawlJob(source="fixture", start_entity="finalization", request_key="test-finalization", status=CrawlStatus.RUNNING.value)
    test_session.add(job)
    await test_session.flush()
    test_session.add_all([
        CrawlFrontierItem(crawl_job_id=job.id, source="fixture", target="done", status=FrontierStatus.COMPLETED.value),
        CrawlFrontierItem(crawl_job_id=job.id, source="fixture", target="retry", status=FrontierStatus.QUEUED.value),
        CrawlFrontierItem(crawl_job_id=job.id, source="fixture", target="bad", status=FrontierStatus.FAILED.value),
    ])
    await test_session.flush()
    await refresh_job_status(test_session, job.id)
    await test_session.refresh(job)
    assert job.status == CrawlStatus.RUNNING.value
    retry = (await test_session.execute(select(CrawlFrontierItem).where(CrawlFrontierItem.target == "retry"))).scalar_one()
    retry.status, retry.completed_at = FrontierStatus.COMPLETED.value, utcnow()
    await refresh_job_status(test_session, job.id)
    await refresh_job_status(test_session, job.id)
    await test_session.refresh(job)
    assert job.status == CrawlStatus.COMPLETED.value
    assert job.entity_count == 2
    assert job.error_message == "1 frontier item(s) failed"
