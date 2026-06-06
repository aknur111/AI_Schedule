import time
import uuid

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import LLMTimeoutError, RetriesExhaustedError
from app.logging_config import get_logger, setup_logging
from app.schemas import ErrorDetail, HealthResponse, ScheduleResponse, WellnessRequest
from app.service import WellnessService

setup_logging(settings.log_level)
logger = get_logger(__name__)

_VERSION = "1.0.0"

app = FastAPI(
    title="Wellness Schedule API",
    version=_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

_service = WellnessService()


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=_VERSION)


@app.post("/schedule", response_model=ScheduleResponse, tags=["schedule"])
async def create_schedule(body: WellnessRequest) -> JSONResponse:
    request_id = str(uuid.uuid4())
    start_ms = time.monotonic() * 1000
    logger.info(
        "request_received",
        extra={"request_id": request_id, "input": body.model_dump()},
    )

    try:
        result = await _service.generate_schedule(body, request_id)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "latency_ms": round(time.monotonic() * 1000 - start_ms, 2),
            },
        )
        return JSONResponse(
            content=result.model_dump(),
            headers={"X-Request-Id": request_id},
        )

    except RetriesExhaustedError as exc:
        logger.error(
            "retries_exhausted",
            extra={
                "request_id": request_id,
                "last_error": exc.last_error,
                "latency_ms": round(time.monotonic() * 1000 - start_ms, 2),
            },
        )
        return JSONResponse(
            status_code=422,
            content=ErrorDetail(
                request_id=request_id,
                error="Failed to generate a valid schedule after maximum retries.",
                code="RETRIES_EXHAUSTED",
            ).model_dump(),
            headers={"X-Request-Id": request_id},
        )

    except LLMTimeoutError:
        logger.warning(
            "request_timeout",
            extra={
                "request_id": request_id,
                "latency_ms": round(time.monotonic() * 1000 - start_ms, 2),
            },
        )
        return JSONResponse(
            status_code=504,
            content=ErrorDetail(
                request_id=request_id,
                error="The LLM request timed out. Try again shortly.",
                code="TIMEOUT",
            ).model_dump(),
            headers={"X-Request-Id": request_id},
        )

    except Exception as exc:
        logger.error(
            "unexpected_error",
            extra={
                "request_id": request_id,
                "error": str(exc),
                "latency_ms": round(time.monotonic() * 1000 - start_ms, 2),
            },
        )
        return JSONResponse(
            status_code=500,
            content=ErrorDetail(
                request_id=request_id,
                error="An unexpected internal error occurred.",
                code="INTERNAL_ERROR",
            ).model_dump(),
            headers={"X-Request-Id": request_id},
        )
