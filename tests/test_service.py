import json
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions import LLMTimeoutError, RetriesExhaustedError
from app.schemas import EnergyLevel, WellnessRequest
from app.service import WellnessService

_VALID_PAYLOAD = json.dumps(
    {
        "schedule": [
            {"time": "09:00", "practice": "Breathing", "duration": 10, "type": "meditation"}
        ]
    }
)

_INVALID_JSON = "not json {{"

_INVALID_SCHEMA = json.dumps(
    {
        "schedule": [
            {"time": "9:00", "practice": "Breathing", "duration": 10, "type": "meditation"}
        ]
    }
)


@pytest.fixture
def service() -> WellnessService:
    return WellnessService()


@pytest.fixture
def valid_request() -> WellnessRequest:
    return WellnessRequest(mood="anxiety", energy=EnergyLevel.low, time_available=30)


async def test_successful_generation_returns_schedule(service, valid_request):
    with patch.object(service._llm, "generate", new=AsyncMock(return_value=_VALID_PAYLOAD)):
        result = await service.generate_schedule(valid_request, "req-001")
    assert len(result.schedule) == 1
    assert result.schedule[0].practice == "Breathing"
    assert result.schedule[0].duration == 10


async def test_retries_on_invalid_json_and_succeeds(service, valid_request):
    mock = AsyncMock(side_effect=[_INVALID_JSON, _INVALID_JSON, _VALID_PAYLOAD])
    with patch.object(service._llm, "generate", mock):
        result = await service.generate_schedule(valid_request, "req-002")
    assert mock.call_count == 3
    assert len(result.schedule) == 1


async def test_retries_on_schema_validation_error_and_succeeds(service, valid_request):
    mock = AsyncMock(side_effect=[_INVALID_SCHEMA, _VALID_PAYLOAD])
    with patch.object(service._llm, "generate", mock):
        result = await service.generate_schedule(valid_request, "req-003")
    assert mock.call_count == 2


async def test_raises_retries_exhausted_after_max_attempts(service, valid_request):
    mock = AsyncMock(return_value=_INVALID_JSON)
    with patch.object(service._llm, "generate", mock):
        with pytest.raises(RetriesExhaustedError) as exc_info:
            await service.generate_schedule(valid_request, "req-004")
    assert exc_info.value.attempts == 3
    assert mock.call_count == 3


async def test_first_attempt_has_no_previous_error(service, valid_request):
    mock = AsyncMock(return_value=_VALID_PAYLOAD)
    with patch.object(service._llm, "generate", mock):
        await service.generate_schedule(valid_request, "req-005")
    assert mock.call_args_list[0].kwargs["previous_error"] is None


async def test_retry_passes_error_message_to_next_prompt(service, valid_request):
    mock = AsyncMock(side_effect=[_INVALID_JSON, _VALID_PAYLOAD])
    with patch.object(service._llm, "generate", mock):
        await service.generate_schedule(valid_request, "req-006")
    assert mock.call_args_list[1].kwargs["previous_error"] is not None
    assert "JSON parse error" in mock.call_args_list[1].kwargs["previous_error"]


async def test_retries_exhausted_error_contains_last_error_message(service, valid_request):
    mock = AsyncMock(return_value=_INVALID_SCHEMA)
    with patch.object(service._llm, "generate", mock):
        with pytest.raises(RetriesExhaustedError) as exc_info:
            await service.generate_schedule(valid_request, "req-007")
    assert "Validation error" in exc_info.value.last_error


async def test_succeeds_on_first_attempt_makes_single_call(service, valid_request):
    mock = AsyncMock(return_value=_VALID_PAYLOAD)
    with patch.object(service._llm, "generate", mock):
        await service.generate_schedule(valid_request, "req-008")
    assert mock.call_count == 1


async def test_timeout_propagates_immediately_without_retry(service, valid_request):
    mock = AsyncMock(side_effect=LLMTimeoutError("timed out"))
    with patch.object(service._llm, "generate", mock):
        with pytest.raises(LLMTimeoutError):
            await service.generate_schedule(valid_request, "req-009")
    assert mock.call_count == 1
