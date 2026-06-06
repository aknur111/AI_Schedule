import json
import time
from typing import Any, Optional

from pydantic import ValidationError

from app.config import settings
from app.exceptions import LLMTimeoutError, RetriesExhaustedError
from app.llm_client import LLMClient
from app.logging_config import get_logger
from app.schemas import ScheduleResponse, WellnessRequest

logger = get_logger(__name__)


class WellnessService:
    def __init__(self) -> None:
        self._llm = LLMClient()

    async def generate_schedule(
        self,
        request: WellnessRequest,
        request_id: str,
    ) -> ScheduleResponse:
        last_error: Optional[str] = None

        for attempt in range(1, settings.max_retries + 1):
            start_ms = time.monotonic() * 1000
            raw_output: str = ""
            success = False
            error_msg: Optional[str] = None

            try:
                raw_output = await self._llm.generate(
                    mood=request.mood,
                    energy=request.energy.value,
                    time_available=request.time_available,
                    request_id=request_id,
                    previous_error=last_error,
                )

                parsed: Any = json.loads(raw_output)
                schedule = ScheduleResponse.model_validate(parsed)
                success = True
                return schedule

            except json.JSONDecodeError as exc:
                error_msg = f"JSON parse error: {exc}"
                last_error = error_msg
            except ValidationError as exc:
                error_msg = f"Validation error: {exc}"
                last_error = error_msg
            except LLMTimeoutError as exc:
                error_msg = str(exc)
                raise

            finally:
                latency_ms = time.monotonic() * 1000 - start_ms
                log_extra: dict[str, Any] = {
                    "request_id": request_id,
                    "attempt": attempt,
                    "input": request.model_dump(),
                    "raw_output": raw_output[:500] if raw_output else "",
                    "success": success,
                    "error": error_msg,
                    "latency_ms": round(latency_ms, 2),
                }
                if success:
                    logger.info("llm_attempt_success", extra=log_extra)
                else:
                    logger.warning("llm_attempt_failed", extra=log_extra)

        raise RetriesExhaustedError(last_error or "unknown error", settings.max_retries)
