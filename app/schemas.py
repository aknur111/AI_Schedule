from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EnergyLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class WellnessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mood: str = Field(..., min_length=1, max_length=50)
    energy: EnergyLevel
    time_available: int = Field(..., ge=5, le=480)


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
