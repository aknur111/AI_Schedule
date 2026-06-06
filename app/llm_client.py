import asyncio
import json
from typing import Optional

from openai import APITimeoutError, AsyncOpenAI

from app.config import settings
from app.exceptions import LLMTimeoutError
from app.logging_config import get_logger

logger = get_logger(__name__)

_MOCK_RESPONSE = json.dumps(
    {
        "schedule": [
            {
                "time": "09:00",
                "practice": "Grounding breathing",
                "duration": 5,
                "type": "meditation",
            },
            {
                "time": "09:05",
                "practice": "Gentle body scan",
                "duration": 10,
                "type": "mindfulness",
            },
            {
                "time": "09:15",
                "practice": "Slow mindful walk",
                "duration": 15,
                "type": "movement",
            },
        ]
    }
)

_SYSTEM_PROMPT = """You are a wellness schedule assistant. Generate a structured daily wellness plan.
Return ONLY valid JSON that matches this exact schema — no markdown, no explanation:
{
  "schedule": [
    {
      "time": "HH:MM",
      "practice": "string",
      "duration": integer_minutes,
      "type": "string"
    }
  ]
}
Rules:
- Times must use 24-hour format with leading zeros (e.g. "09:00", "14:30").
- Durations must be positive integers between 1 and 120.
- The sum of all durations must equal the requested total time exactly.
- No extra fields beyond the four listed above."""


def _build_user_prompt(
    mood: str,
    energy: str,
    time_available: int,
    previous_error: Optional[str] = None,
) -> str:
    prompt = (
        f"Generate a wellness schedule for someone feeling '{mood}' "
        f"with '{energy}' energy level and exactly {time_available} minutes available. "
        f"Distribute practices so total duration sums to {time_available} minutes."
    )
    if previous_error:
        prompt += (
            f"\n\nYour previous response was rejected. Fix this exact error:\n{previous_error}"
        )
    return prompt


class LLMClient:
    def __init__(self) -> None:
        self._client: Optional[AsyncOpenAI] = None
        if not settings.mock_llm:
            self._client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_timeout,
            )

    async def generate(
        self,
        mood: str,
        energy: str,
        time_available: int,
        request_id: str,
        previous_error: Optional[str] = None,
    ) -> str:
        if settings.mock_llm:
            await asyncio.sleep(0.05)
            return _MOCK_RESPONSE

        user_prompt = _build_user_prompt(mood, energy, time_available, previous_error)
        try:
            response = await self._client.chat.completions.create( 
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                extra_headers={"X-Request-Id": request_id},
            )
            return response.choices[0].message.content or ""
        except APITimeoutError as exc:
            raise LLMTimeoutError(
                f"OpenAI request timed out after {settings.openai_timeout}s"
            ) from exc
