from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnergyLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


_ENERGY_RU_MAP: dict[str, str] = {
    "низкая": "low",
    "средняя": "medium",
    "высокая": "high",
}


class WellnessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mood: str = Field(..., min_length=1, max_length=50)
    energy: EnergyLevel
    time_available: int = Field(..., ge=5, le=480)

    @field_validator("energy", mode="before")
    @classmethod
    def normalize_energy(cls, v: object) -> object:
        if isinstance(v, str):
            return _ENERGY_RU_MAP.get(v.lower(), v)
        return v


class PracticeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    practice: str = Field(..., min_length=1)
    duration: int = Field(..., ge=1, le=120)
    type: str = Field(..., min_length=1)


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule: list[PracticeItem] = Field(..., min_length=1, max_length=20)


class ErrorDetail(BaseModel):
    request_id: str
    error: str
    code: str


class HealthResponse(BaseModel):
    status: str
    version: str
