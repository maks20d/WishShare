from fastapi.testclient import TestClient

from app.main import app


def test_web_vitals_ok(test_client: TestClient):
    res = test_client.post("/metrics/web-vitals", json={"name": "CLS", "value": 0.12})
    assert res.status_code == 200
    assert res.json().get("status") == "ok"


def test_web_vitals_ignored(test_client: TestClient):
    res = test_client.post("/metrics/web-vitals", json={"name": 123, "value": "bad"})
    assert res.status_code == 200
    assert res.json().get("status") == "ignored"
