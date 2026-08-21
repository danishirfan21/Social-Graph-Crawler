from arq import create_pool
import logging

from arq.connections import RedisSettings

from app.config import settings

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

    async def disconnect(self):
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    async def enqueue_frontier(self, job_id: str, frontier_ids: list[str]) -> None:
        if self.redis is None:
            raise RuntimeError("task queue is unavailable")
        for frontier_id in frontier_ids:
            task = await self.redis.enqueue_job("process_frontier_item", job_id, frontier_id)
            logger.info("frontier.enqueued crawl_job_id=%s frontier_item_id=%s arq_job_id=%s", job_id, frontier_id, task.job_id)


task_queue = TaskQueue()
