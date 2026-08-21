async def test_create_node_and_reject_duplicate(client, sample_node_data):
    created = await client.post("/api/v1/nodes/", json=sample_node_data)
    assert created.status_code == 201
    duplicate = await client.post("/api/v1/nodes/", json=sample_node_data)
    assert duplicate.status_code == 409

