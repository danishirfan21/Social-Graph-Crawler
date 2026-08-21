from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api import crawl
from app import worker


class FakeRedis:
    def __init__(self): self.enqueued = []
    async def set(self, *args, **kwargs): return True
    async def enqueue_job(self, *args, **kwargs): self.enqueued.append((args, kwargs))


async def test_v2_job_creates_deduplicated_frontier_and_records_failures(client, test_engine, monkeypatch):
    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async def enqueue(job_id, count): pass
    monkeypatch.setattr(crawl.task_queue, "enqueue_frontier", enqueue)
    monkeypatch.setattr(worker, "AsyncSessionLocal", sessionmaker)
    response = await client.post("/api/v1/crawl/start", json={"source": "fixture", "start_entity": "v2-demo", "depth": 2, "max_entities": 10})
    assert response.status_code == 202
    job_id = response.json()["id"]
    frontier = await client.get(f"/api/v1/crawl/jobs/{job_id}/frontier")
    assert len(frontier.json()) == 4  # duplicate fixture target is constrained per job
    redis = FakeRedis()
    for item in frontier.json():
        await worker.process_frontier_item({"redis": redis}, job_id, item["id"])
    transient_id = next(item["id"] for item in frontier.json() if item["target"] == "transient")
    await worker.process_frontier_item({"redis": redis}, job_id, transient_id)
    await worker.process_frontier_item({"redis": redis}, job_id, transient_id)
    job = (await client.get(f"/api/v1/crawl/jobs/{job_id}")).json()
    assert job["status"] == "completed"
    failures = (await client.get(f"/api/v1/crawl/jobs/{job_id}/failures")).json()
    assert len(failures) == 1
    transient = [item for item in (await client.get(f"/api/v1/crawl/jobs/{job_id}/frontier")).json() if item["target"] == "transient"][0]
    assert transient["attempt_count"] == 3


async def test_active_duplicate_job_is_rejected(client, monkeypatch):
    async def enqueue(job_id, count): pass
    monkeypatch.setattr(crawl.task_queue, "enqueue_frontier", enqueue)
    payload = {"source": "fixture", "start_entity": "success", "depth": 2, "max_entities": 10}
    assert (await client.post("/api/v1/crawl/start", json=payload)).status_code == 202
    assert (await client.post("/api/v1/crawl/start", json=payload)).status_code == 409
