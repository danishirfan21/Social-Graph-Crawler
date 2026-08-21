"""Crawl job API and in-process development runner (not a distributed queue)."""
from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.fixture_crawler import FixtureCrawler
from app.crawlers.github_crawler import GitHubCrawler
from app.crawlers.reddit_crawler import RedditCrawler
from app.crawlers.wikipedia_crawler import WikipediaCrawler
from app.database import AsyncSessionLocal, get_db
from app.models import CrawlJob, CrawlStatus

router = APIRouter()
SUPPORTED_SOURCES = ("fixture", "reddit", "github", "wikipedia")

class CrawlRequest(BaseModel):
    source: Literal["fixture", "reddit", "github", "wikipedia"]
    start_entity: str = Field(min_length=1, max_length=255)
    depth: int = Field(default=2, ge=1, le=5)
    max_entities: int = Field(default=100, ge=1, le=5000)

class CrawlJobResponse(BaseModel):
    id: UUID
    source: str
    start_entity: str
    status: str
    entity_count: int
    edge_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

def request_key(request: CrawlRequest) -> str:
    canonical = f"{request.source}|{request.start_entity.strip().lower()}|{request.depth}|{request.max_entities}"
    return sha256(canonical.encode()).hexdigest()

def crawler_for(source: str, db: AsyncSession):
    crawlers = {"fixture": FixtureCrawler, "reddit": RedditCrawler, "github": GitHubCrawler, "wikipedia": WikipediaCrawler}
    return crawlers[source](db, rate_limit=5.0)

async def run_crawler_task(job_id: UUID, request: CrawlRequest) -> None:
    """Run one job with a fresh session and preserve a failure record."""
    async with AsyncSessionLocal() as db:
        job = await db.get(CrawlJob, job_id)
        if job is None or job.status == CrawlStatus.CANCELLED.value:
            return
        try:
            async with crawler_for(request.source, db) as crawler:
                await crawler.crawl(request.start_entity, request.depth, request.max_entities, job=job)
        except Exception as exc:
            await db.rollback()
            job = await db.get(CrawlJob, job_id)
            if job and job.status != CrawlStatus.CANCELLED.value:
                job.status = CrawlStatus.FAILED.value
                job.error_message = str(exc)[:2000]
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()

@router.post("/start", response_model=CrawlJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    key = request_key(request)
    existing = (await db.execute(select(CrawlJob).where(CrawlJob.request_key == key))).scalar_one_or_none()
    if existing and not existing.is_finished:
        raise HTTPException(status_code=409, detail="An identical crawl is already pending or running")
    job = CrawlJob(source=request.source, start_entity=request.start_entity.strip(), request_key=key, status=CrawlStatus.PENDING.value)
    db.add(job)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="An identical crawl is already pending or running")
    await db.refresh(job)
    background_tasks.add_task(run_crawler_task, job.id, request)
    return job

@router.get("/jobs", response_model=list[CrawlJobResponse])
async def list_crawl_jobs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), source: str | None = Query(None), job_status: str | None = Query(None, alias="status"), db: AsyncSession = Depends(get_db)):
    query = select(CrawlJob).order_by(desc(CrawlJob.created_at)).offset((page - 1) * page_size).limit(page_size)
    if source:
        if source not in SUPPORTED_SOURCES:
            raise HTTPException(422, "Unsupported source")
        query = query.where(CrawlJob.source == source)
    if job_status:
        query = query.where(CrawlJob.status == job_status)
    return (await db.execute(query)).scalars().all()

@router.get("/jobs/{job_id}", response_model=CrawlJobResponse)
async def get_crawl_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(CrawlJob, job_id)
    if job is None:
        raise HTTPException(404, "Crawl job not found")
    return job

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_crawl_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(CrawlJob, job_id)
    if job is None:
        raise HTTPException(404, "Crawl job not found")
    if job.is_finished:
        raise HTTPException(400, "Cannot cancel a finished job")
    job.status, job.completed_at = CrawlStatus.CANCELLED.value, datetime.now(timezone.utc)
    await db.commit()
