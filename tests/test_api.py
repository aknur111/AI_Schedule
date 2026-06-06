import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.exceptions import LLMTimeoutError
from app.main import _service, app

_VALID_PAYLOAD = json.dumps(
    {
        "schedule": [
            {"time": "09:00", "practice": "Breathing", "duration": 10, "type": "meditation"}
        ]
    }
)

_INVALID_JSON = "not json {{"

_SCHEDULE_BODY = {"mood": "anxiety", "energy": "low", "time_available": 30}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_schedule_returns_200_with_valid_body(client):
    response = await client.post("/schedule", json=_SCHEDULE_BODY)
    assert response.status_code == 200
    body = response.json()
    assert "schedule" in body
    assert isinstance(body["schedule"], list)
    assert len(body["schedule"]) > 0


async def test_schedule_response_carries_request_id_header(client):
    response = await client.post("/schedule", json=_SCHEDULE_BODY)
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) == 36


async def test_schedule_validates_unknown_energy_level(client):
    response = await client.post(
        "/schedule", json={"mood": "calm", "energy": "extreme", "time_available": 30}
    )
    assert response.status_code == 422


async def test_schedule_validates_time_available_below_minimum(client):
    response = await client.post(
        "/schedule", json={"mood": "calm", "energy": "low", "time_available": 1}
    )
    assert response.status_code == 422


async def test_schedule_rejects_extra_fields_in_body(client):
    response = await client.post(
        "/schedule",
        json={"mood": "calm", "energy": "low", "time_available": 30, "injected": "extra"},
    )
    assert response.status_code == 422


async def test_schedule_retries_exhausted_returns_422_with_error_body(client):
    mock = AsyncMock(return_value=_INVALID_JSON)
    with patch.object(_service._llm, "generate", mock):
        response = await client.post("/schedule", json=_SCHEDULE_BODY)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "RETRIES_EXHAUSTED"
    assert "request_id" in body
    assert "error" in body
    assert "x-request-id" in response.headers


async def test_schedule_timeout_returns_504_with_error_body(client):
    mock = AsyncMock(side_effect=LLMTimeoutError("timed out"))
    with patch.object(_service._llm, "generate", mock):
        response = await client.post("/schedule", json=_SCHEDULE_BODY)
    assert response.status_code == 504
    body = response.json()
    assert body["code"] == "TIMEOUT"
    assert "request_id" in body
    assert "x-request-id" in response.headers


async def test_schedule_practice_items_have_correct_shape(client):
    response = await client.post("/schedule", json=_SCHEDULE_BODY)
    assert response.status_code == 200
    for item in response.json()["schedule"]:
        assert "time" in item
        assert "practice" in item
        assert "duration" in item
        assert "type" in item
        assert isinstance(item["duration"], int)
