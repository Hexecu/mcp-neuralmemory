import base64
from datetime import datetime, timezone
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from kg_mcp.api import create_api_app
from kg_mcp.config import get_settings


class FakeRepository:
    def __init__(self, *, fail=False, last_screenshot=None):
        self.fail = fail
        self.last_screenshot = last_screenshot
        self.events = []
        self.slices = []

    async def get_last_screenshot_event(self, project_id):
        return self.last_screenshot

    async def upsert_raw_event(self, **event):
        if self.fail:
            raise RuntimeError("database details must remain private")
        self.events.append(event)
        return {"id": "event-1", "type": event["event_type"]}

    async def upsert_activity_slice(self, **activity_slice):
        self.slices.append(activity_slice)
        return {"id": "slice-1"}


def client(monkeypatch, repository=None, token="test-token"):
    monkeypatch.setenv("KG_MCP_TOKEN", token)
    monkeypatch.setenv("LLM_ENABLED", "false")
    get_settings.cache_clear()
    repository = repository or FakeRepository()
    return TestClient(create_api_app(lambda: repository)), repository


def test_health_has_stable_product_identity(monkeypatch):
    http, _ = client(monkeypatch)
    response = http.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "neural-memory", "version": "0.2.0"}


def test_private_routes_require_the_configured_token(monkeypatch):
    http, _ = client(monkeypatch)
    payload = {"event_type": "window_focus"}
    assert http.post("/api/ingest/event", json=payload).status_code == 401
    assert (
        http.post(
            "/api/ingest/event", json=payload, headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 403
    )
    assert (
        http.post(
            "/api/ingest/event", json=payload, headers={"Authorization": "Basic test-token"}
        ).status_code
        == 401
    )


def test_unconfigured_server_fails_closed(monkeypatch):
    http, _ = client(monkeypatch, token="")
    response = http.post("/api/ingest/event", json={"event_type": "window_focus"})
    assert response.status_code == 503


def test_ingest_validates_and_normalizes_an_event(monkeypatch):
    http, repository = client(monkeypatch)
    response = http.post(
        "/api/ingest/event",
        headers={"Authorization": "Bearer test-token"},
        json={
            "project_id": "demo",
            "event_type": "window_focus",
            "timestamp": "2026-09-03T10:30:00+02:00",
            "data": {"app": "Editor"},
            "text_content": "A deliberately harmless test event",
        },
    )
    assert response.status_code == 200
    assert response.json()["id"] == "event-1"
    assert repository.events[0]["timestamp"] == datetime(2026, 9, 3, 8, 30, tzinfo=timezone.utc)


def test_naive_timestamps_are_treated_as_utc(monkeypatch):
    http, repository = client(monkeypatch)
    response = http.post(
        "/api/ingest/event",
        headers={"Authorization": "Bearer test-token"},
        json={"event_type": "focus", "timestamp": "2026-09-03T08:30:00"},
    )
    assert response.status_code == 200
    assert repository.events[0]["timestamp"].tzinfo == timezone.utc


def test_unknown_fields_and_invalid_time_ranges_are_rejected(monkeypatch):
    http, _ = client(monkeypatch)
    headers = {"Authorization": "Bearer test-token"}
    assert (
        http.post(
            "/api/ingest/event", headers=headers, json={"event_type": "focus", "surprise": True}
        ).status_code
        == 422
    )
    assert (
        http.post(
            "/api/ingest/slice",
            headers=headers,
            json={"start_time": "2026-09-03T11:00:00Z", "end_time": "2026-09-03T10:00:00Z"},
        ).status_code
        == 422
    )


def test_payload_limits_are_enforced(monkeypatch):
    monkeypatch.setenv("MAX_TEXT_CHARS", "8")
    get_settings.cache_clear()
    http, _ = client(monkeypatch)
    response = http.post(
        "/api/ingest/event",
        headers={"Authorization": "Bearer test-token"},
        json={"event_type": "typing", "text_content": "nine chars"},
    )
    assert response.status_code == 422


def test_declared_request_size_is_rejected_before_parsing(monkeypatch):
    http, _ = client(monkeypatch)
    response = http.post(
        "/api/ingest/event",
        content=b"{}",
        headers={"Authorization": "Bearer test-token", "Content-Length": "12000001"},
    )
    assert response.status_code == 413


def test_valid_slice_is_forwarded_to_the_repository(monkeypatch):
    http, repository = client(monkeypatch)
    response = http.post(
        "/api/ingest/slice",
        headers={"Authorization": "Bearer test-token"},
        json={
            "project_id": "demo",
            "start_time": "2026-09-03T08:00:00Z",
            "end_time": "2026-09-03T08:05:00Z",
            "summary": "Synthetic test activity",
            "event_ids": ["event-1"],
        },
    )
    assert response.status_code == 200
    assert response.json() == {"id": "slice-1"}
    assert repository.slices[0]["project_id"] == "demo"


def screenshot_base64() -> str:
    output = BytesIO()
    Image.new("RGB", (2, 2), "white").save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode()


def test_invalid_screenshot_is_rejected(monkeypatch):
    http, repository = client(monkeypatch)
    response = http.post(
        "/api/ingest/event",
        headers={"Authorization": "Bearer test-token"},
        json={
            "event_type": "focus",
            "data": {"has_screenshot": "true"},
            "screenshot_base64": "not-an-image",
        },
    )
    assert response.status_code == 422
    assert repository.events == []


def test_duplicate_screenshot_is_linked_without_storing_pixels(monkeypatch):
    repository = FakeRepository(
        last_screenshot={
            "id": "previous-event",
            "timestamp": "2026-09-03T08:29:30Z",
            "screenshot_hash": "0000000000000000",
        }
    )
    http, repository = client(monkeypatch, repository)
    response = http.post(
        "/api/ingest/event",
        headers={"Authorization": "Bearer test-token"},
        json={
            "event_type": "focus",
            "timestamp": "2026-09-03T08:30:00Z",
            "data": {"has_screenshot": True},
            "screenshot_base64": screenshot_base64(),
        },
    )
    assert response.status_code == 200
    stored = repository.events[0]
    assert stored["is_duplicate"] is True
    assert stored["duplicate_of"] == "previous-event"
    assert "screenshot_base64" not in stored


def test_storage_errors_do_not_leak_internal_details(monkeypatch):
    http, _ = client(monkeypatch, FakeRepository(fail=True))
    response = http.post(
        "/api/ingest/event",
        headers={"Authorization": "Bearer test-token"},
        json={"event_type": "focus"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Memory store is unavailable"}
    assert "database details" not in response.text
