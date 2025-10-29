"""
API routes for triggering and monitoring crawler jobs.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import CrawlJob, CrawlStatus
from app.crawlers.reddit_crawler import RedditCrawler


router = APIRouter()


class CrawlRequest(BaseModel):
    """Request to start a crawl job."""
    source: str = Field(..., pattern="^(reddit|github|wikipedia)$", description="Data source")
    start_entity: str = Field(..., min_length=1, description="Starting entity (subreddit, user, repo)")
    depth: int = Field(default=2, ge=1, le=5, description="Crawl depth")
    max_entities: int = Field(default=100, ge=1, le=5000, description="Max entities to discover")


class CrawlJobResponse(BaseModel):
    """Crawl job response."""
    id: UUID
    source: str
    status: str
    entity_count: int
    edge_count: int
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    
    class Config:
        from_attributes = True


async def run_crawler_task(
    source: str,
    start_entity: str,
    depth: int,
    max_entities: int,
    db_url: str
):
    """Background task to run crawler."""
    from app.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            if source == "reddit":
                async with RedditCrawler(db, rate_limit=1.0) as crawler:
                    await crawler.crawl(start_entity, depth, max_entities)
            # Add other crawlers here
            # elif source == "github":
            #     async with GitHubCrawler(db, rate_limit=5.0) as crawler:
            #         await crawler.crawl(start_entity, depth, max_entities)
            else:
                raise ValueError(f"Unsupported source: {source}")
        except Exception as e:
            # Error is already logged in crawler
            pass


@router.post("/start", response_model=CrawlJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new crawl job.
    
    The job runs asynchronously in the background.
    Use the returned job ID to check status.
    
    - **source**: Data source (reddit, github, wikipedia)
    - **start_entity**: Starting point (e.g., subreddit name)
    - **depth**: How many levels to crawl
    - **max_entities**: Maximum entities to discover
    """
    # Create job record
    job = CrawlJob(
        source=request.source,
        status=CrawlStatus.PENDING.value
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Schedule background task
    from app.config import settings
    background_tasks.add_task(
        run_crawler_task,
        request.source,
        request.start_entity,
        request.depth,
        request.max_entities,
        settings.DATABASE_URL
    )
    
    return job


@router.get("/jobs", response_model=List[CrawlJobResponse])
async def list_crawl_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str | None = Query(None, pattern="^(reddit|github|wikipedia)$"),
    status: str | None = Query(None, pattern="^(pending|running|completed|failed|cancelled)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    List crawl jobs with pagination and filtering.
    """
    query = select(CrawlJob)
    
    if source:
        query = query.where(CrawlJob.source == source)
    
    if status:
        query = query.where(CrawlJob.status == status)
    
    # Order by created_at descending
    query = query.order_by(desc(CrawlJob.created_at))
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return jobs


@router.get("/jobs/{job_id}", response_model=CrawlJobResponse)
async def get_crawl_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get crawl job status by ID.
    """
    result = await db.execute(
        select(CrawlJob).where(CrawlJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crawl job {job_id} not found"
        )
    
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_crawl_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a crawl job (if still pending/running).
    """
    result = await db.execute(
        select(CrawlJob).where(CrawlJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crawl job {job_id} not found"
        )
    
    if job.is_finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a finished job"
        )
    
    job.status = CrawlStatus.CANCELLED.value
    from datetime import datetime
    if not job.completed_at:
        job.completed_at = datetime.utcnow()
    
    await db.commit()