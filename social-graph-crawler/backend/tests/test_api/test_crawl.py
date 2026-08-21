from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api import crawl


async def test_fixture_job_runs_and_persists_results(client, test_engine, monkeypatch):
    monkeypatch.setattr(crawl, "AsyncSessionLocal", async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False))
    response = await client.post("/api/v1/crawl/start", json={"source": "fixture", "start_entity": "Python", "depth": 2, "max_entities": 10})
    assert response.status_code == 202
    job = response.json()
    assert job["status"] == "pending"
    result = await client.get(f"/api/v1/crawl/jobs/{job['id']}")
    assert result.json()["status"] == "completed"
    assert result.json()["entity_count"] == 2


async def test_fixture_job_failure_is_recorded(client, test_engine, monkeypatch):
    monkeypatch.setattr(crawl, "AsyncSessionLocal", async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False))
    response = await client.post("/api/v1/crawl/start", json={"source": "fixture", "start_entity": "fail", "depth": 2, "max_entities": 10})
    job_id = response.json()["id"]
    result = await client.get(f"/api/v1/crawl/jobs/{job_id}")
    assert result.json()["status"] == "failed"
    assert "instructed to fail" in result.json()["error_message"]
