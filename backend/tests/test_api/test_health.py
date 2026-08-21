async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


async def test_metrics_endpoint(client):
    response = await client.get("/metrics")
    assert response.status_code in {200, 307}
