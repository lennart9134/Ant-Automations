"""Smoke tests for the vision service API."""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "vision"


def test_analyze_image_placeholder():
    resp = client.post("/api/v1/vision/analyze", json={"image_url": "https://example.com/doc.png"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "phi-4-reasoning-vision-15b"
    assert data["status"] == "placeholder"
