import pytest
from pydantic import ValidationError

from app.schemas import EnergyLevel, PracticeItem, ScheduleResponse, WellnessRequest


def test_valid_request_parses_correctly():
    req = WellnessRequest(mood="anxiety", energy="low", time_available=30)
    assert req.mood == "anxiety"
    assert req.energy == EnergyLevel.low
    assert req.time_available == 30


def test_request_rejects_unknown_energy_level():
    with pytest.raises(ValidationError):
        WellnessRequest(mood="happy", energy="extreme", time_available=30)


def test_request_rejects_time_below_minimum():
    with pytest.raises(ValidationError):
        WellnessRequest(mood="calm", energy="medium", time_available=1)


def test_request_rejects_time_above_maximum():
    with pytest.raises(ValidationError):
        WellnessRequest(mood="calm", energy="medium", time_available=600)


def test_request_rejects_empty_mood():
    with pytest.raises(ValidationError):
        WellnessRequest(mood="", energy="medium", time_available=30)


def test_valid_schedule_response_parses():
    data = {
        "schedule": [
            {"time": "09:00", "practice": "Breathing", "duration": 10, "type": "meditation"}
        ]
    }
    resp = ScheduleResponse.model_validate(data)
    assert len(resp.schedule) == 1
    assert resp.schedule[0].practice == "Breathing"


def test_schedule_rejects_empty_list():
    with pytest.raises(ValidationError):
        ScheduleResponse.model_validate({"schedule": []})


def test_schedule_rejects_malformed_time():
    with pytest.raises(ValidationError):
        ScheduleResponse.model_validate(
            {
                "schedule": [
                    {"time": "9:00", "practice": "Breathing", "duration": 10, "type": "meditation"}
                ]
            }
        )


def test_schedule_rejects_single_digit_time():
    with pytest.raises(ValidationError):
        ScheduleResponse.model_validate(
            {
                "schedule": [
                    {"time": "9:5", "practice": "Test", "duration": 5, "type": "test"}
                ]
            }
        )


def test_practice_item_rejects_duration_over_limit():
    with pytest.raises(ValidationError):
        PracticeItem(time="09:00", practice="Test", duration=200, type="test")


def test_practice_item_rejects_zero_duration():
    with pytest.raises(ValidationError):
        PracticeItem(time="09:00", practice="Test", duration=0, type="test")


def test_multiple_practice_items_validate():
    data = {
        "schedule": [
            {"time": "09:00", "practice": "Breathing", "duration": 5, "type": "meditation"},
            {"time": "09:05", "practice": "Stretching", "duration": 10, "type": "movement"},
            {"time": "09:15", "practice": "Journaling", "duration": 15, "type": "reflection"},
        ]
    }
    resp = ScheduleResponse.model_validate(data)
    assert len(resp.schedule) == 3


def test_russian_energy_low_normalizes_to_enum():
    req = WellnessRequest(mood="тревога", energy="низкая", time_available=30)
    assert req.energy == EnergyLevel.low


def test_russian_energy_medium_normalizes_to_enum():
    req = WellnessRequest(mood="стресс", energy="средняя", time_available=20)
    assert req.energy == EnergyLevel.medium


def test_russian_energy_high_normalizes_to_enum():
    req = WellnessRequest(mood="спокойствие", energy="высокая", time_available=60)
    assert req.energy == EnergyLevel.high


def test_invalid_russian_energy_is_rejected():
    with pytest.raises(ValidationError):
        WellnessRequest(mood="стресс", energy="очень высокая", time_available=30)
