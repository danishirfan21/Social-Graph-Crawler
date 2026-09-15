"""Durable V2 crawl job API: PostgreSQL job/frontier plus Redis ARQ enqueue."""
from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import CrawlFrontierItem, CrawlJob, CrawlStatus, FrontierStatus
from app.services.frontier_service import add_frontier_item, frontier_counts, recover_stale_items
from app.services.queue import task_queue

router = APIRouter()

class CrawlRequest(BaseModel):
    source: Literal["fixture", "reddit", "github", "wikipedia"]
    start_entity: str = Field(min_length=1, max_length=255)
    depth: int = Field(default=2, ge=1, le=5)
    max_entities: int = Field(default=100, ge=1, le=5000)

class CrawlJobResponse(BaseModel):
    id: UUID; source: str; start_entity: str; status: str; entity_count: int; edge_count: int
    error_message: str | None; started_at: datetime | None; completed_at: datetime | None; created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FrontierResponse(BaseModel):
    id: UUID; target: str; source: str; depth: int; max_entities: int; status: str; attempt_count: int; last_error: str | None
    model_config = ConfigDict(from_attributes=True)

def request_key(request: CrawlRequest) -> str:
    return sha256(f"{request.source}|{request.start_entity.strip().lower()}|{request.depth}|{request.max_entities}".encode()).hexdigest()

def fixture_targets(entity: str) -> list[str]:
    if entity == "v2-demo" or entity.startswith("v2-demo-"):
        return ["success", "transient", "permanent", "duplicate", "duplicate"]
    if entity == "slow-demo":
        return ["slow", "slow", "success"]
    return ["success"]

@router.post("/start", response_model=CrawlJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_crawl(request: CrawlRequest, db: AsyncSession = Depends(get_db)):
    key = request_key(request)
    active = (await db.execute(select(CrawlJob).where(CrawlJob.request_key == key, CrawlJob.status.in_([CrawlStatus.PENDING.value, CrawlStatus.RUNNING.value])))).scalar_one_or_none()
    if active:
        raise HTTPException(409, "An identical crawl is already active")
    job = CrawlJob(source=request.source, start_entity=request.start_entity.strip(), request_key=key, status=CrawlStatus.RUNNING.value, started_at=datetime.now(timezone.utc))
    db.add(job)
    try:
        await db.flush()
        targets = fixture_targets(request.start_entity) if request.source == "fixture" else [request.start_entity]
        frontier_ids = [
            item_id
            for target in targets
            if (item_id := await add_frontier_item(
                db, job.id, request.source, target, request.depth, request.max_entities
            ))
        ]
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "An identical crawl is already active")
    try:
        await task_queue.enqueue_frontier(str(job.id), [str(item_id) for item_id in frontier_ids])
    except Exception as exc:
        job.status, job.error_message = CrawlStatus.FAILED.value, f"Queue enqueue failed: {exc}"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(503, "Task queue is unavailable")
    await db.refresh(job)
    return job

@router.get("/jobs/{job_id}", response_model=CrawlJobResponse)
async def get_crawl_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(CrawlJob, job_id)
    if not job: raise HTTPException(404, "Crawl job not found")
    return job

@router.get("/jobs/{job_id}/frontier", response_model=list[FrontierResponse])
async def get_frontier(job_id: UUID, db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(CrawlFrontierItem).where(CrawlFrontierItem.crawl_job_id == job_id).order_by(CrawlFrontierItem.discovered_at))).scalars().all()

@router.get("/jobs/{job_id}/failures", response_model=list[FrontierResponse])
async def get_failures(job_id: UUID, db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(CrawlFrontierItem).where(CrawlFrontierItem.crawl_job_id == job_id, CrawlFrontierItem.status == FrontierStatus.FAILED.value))).scalars().all()

@router.post("/jobs/{job_id}/resume", response_model=CrawlJobResponse)
async def resume_crawl(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(CrawlJob, job_id)
    if not job: raise HTTPException(404, "Crawl job not found")
    recovered = await recover_stale_items(db, job_id)
    await db.commit()
    queued_ids = (await db.execute(select(CrawlFrontierItem.id).where(CrawlFrontierItem.crawl_job_id == job_id, CrawlFrontierItem.status == FrontierStatus.QUEUED.value))).scalars().all()
    await task_queue.enqueue_frontier(str(job_id), [str(item_id) for item_id in queued_ids])
    return job

@router.get("/jobs", response_model=list[CrawlJobResponse])
async def list_crawl_jobs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(CrawlJob).order_by(desc(CrawlJob.created_at)).offset((page - 1) * page_size).limit(page_size))).scalars().all()
