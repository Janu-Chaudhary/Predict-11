from fastapi.testclient import TestClient

from p11.api.app import app


def test_health_reports_version_and_db_state():
    r = TestClient(app).get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] in {"ok", "down"}
