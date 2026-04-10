"""Smoke tests for the workers service API."""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "workers"


def test_worker_status():
    resp = client.get("/api/v1/workers/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "pool_size" in data
    assert "active" in data
    assert "queued" in data
