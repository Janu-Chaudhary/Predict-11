from fastapi.testclient import TestClient

from p11.api.app import app


def test_health_reports_version_and_db_state():
    r = TestClient(app).get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] in {"ok", "down"}


def test_cors_allows_any_local_port_in_dev():
    client = TestClient(app)
    for origin in ("http://localhost:3001", "http://127.0.0.1:5173", "http://localhost:3000"):
        r = client.get("/api/v1/health", headers={"Origin": origin})
        assert r.headers.get("access-control-allow-origin") == origin
    r = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_regex_is_off_outside_dev():
    from p11.core.settings import Settings

    assert Settings(env="prod").effective_cors_origin_regex is None
    assert Settings(env="prod", cors_origin_regex=r"^https://x\.app$").effective_cors_origin_regex
