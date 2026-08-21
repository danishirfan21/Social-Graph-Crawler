"""
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.services.cache_service import cache
from app.services.metrics import metrics_app
from app.services.queue import task_queue
from app.api import nodes, edges, graph, crawl


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting up Social Graph Crawler API...")
    await init_db()
    await cache.connect()
    await task_queue.connect()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    await cache.disconnect()
    await task_queue.disconnect()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API for crawling and analyzing social graphs from public data sources",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)
app.mount("/metrics", metrics_app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Check if the API is running."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Report dependencies required to accept crawl jobs."""
    from sqlalchemy import text
    from app.database import engine
    database_ok = redis_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        logger.exception("readiness database check failed")
    try:
        redis_ok = bool(cache.redis and await cache.redis.ping())
    except Exception:
        logger.exception("readiness Redis check failed")
    if not (database_ok and redis_ok):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": database_ok, "redis": redis_ok})
    return {"status": "ready", "database": True, "redis": True}


# Include routers
app.include_router(
    nodes.router,
    prefix=f"{settings.API_V1_PREFIX}/nodes",
    tags=["Nodes"]
)

app.include_router(
    edges.router,
    prefix=f"{settings.API_V1_PREFIX}/edges",
    tags=["Edges"]
)

app.include_router(
    graph.router,
    prefix=f"{settings.API_V1_PREFIX}/graph",
    tags=["Graph"]
)

app.include_router(
    crawl.router,
    prefix=f"{settings.API_V1_PREFIX}/crawl",
    tags=["Crawler"]
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
