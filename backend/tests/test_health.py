def test_healthz(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_readyz_returns_200_when_dependencies_healthy(client):
    response = client.get("/api/v1/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]


def test_readyz_returns_503_when_required_db_check_fails(client, monkeypatch):
    """RC1 Phase 0 — Security Remediation (Finding 6): database is the one
    REQUIRED readiness dependency — a broken DB connection must fail the
    HTTP status code (not just change a JSON field), so a standard
    orchestrator readiness probe actually takes the instance out of
    rotation."""
    import app.api.v1.health as health_module
    monkeypatch.setattr(health_module, "check_db_connection", lambda: False)

    response = client.get("/api/v1/readyz")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["database"] == "error"


def test_readyz_ignores_redis_failure_per_documented_optional_policy(client, monkeypatch):
    """Redis is documented as OPTIONAL for readiness (see
    app/api/v1/health.py's docstring — nothing in the running app
    currently depends on it). A Redis outage must be visible in the
    response body but must never fail readiness on its own."""
    import app.api.v1.health as health_module
    monkeypatch.setattr(health_module, "check_redis_connection", lambda: False)

    response = client.get("/api/v1/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["redis"] == "unavailable"


def test_readyz_503_even_if_redis_also_down_alongside_db(client, monkeypatch):
    """Required-dependency failure must win regardless of the optional
    dependency's state."""
    import app.api.v1.health as health_module
    monkeypatch.setattr(health_module, "check_db_connection", lambda: False)
    monkeypatch.setattr(health_module, "check_redis_connection", lambda: False)

    response = client.get("/api/v1/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_openapi_schema(client):
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Construction AI Platform"


def test_docs_available(client):
    response = client.get("/api/docs")
    assert response.status_code == 200
