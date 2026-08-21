from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings


class TaskQueue:
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

    async def disconnect(self):
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    async def enqueue_frontier(self, job_id: str, count: int) -> None:
        if self.redis is None:
            raise RuntimeError("task queue is unavailable")
        for _ in range(count):
            await self.redis.enqueue_job("process_frontier_item", job_id)


task_queue = TaskQueue()
