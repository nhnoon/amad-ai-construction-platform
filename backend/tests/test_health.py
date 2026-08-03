def test_healthz(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_readyz(client):
    response = client.get("/api/v1/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "degraded")
    assert "checks" in data
    assert "database" in data["checks"]


def test_openapi_schema(client):
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Construction AI Platform"


def test_docs_available(client):
    response = client.get("/api/docs")
    assert response.status_code == 200
