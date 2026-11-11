import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from src.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, BASE_URL


client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=BASE_URL,
    max_retries=0,
)


@dataclass
class LLMResult:
    data: Dict[str, Any]
    usage: Optional[Dict[str, int]] = None


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text or not text.strip():
        return None
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def chat_json(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    retries: int = 2,
) -> LLMResult:
    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 2):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content or ""
            parsed = _extract_json(content)
            if parsed is None:
                raise ValueError(
                    f"Модель вернула не-JSON или пустой ответ: {content[:300]!r}"
                )

            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            return LLMResult(data=parsed, usage=usage)

        except (APIError, APITimeoutError, RateLimitError) as e:
            last_error = e
            if attempt <= retries:
                continue
            raise RuntimeError(
                f"Ошибка DeepSeek API после {retries + 1} попыток: {e}"
            ) from e
        except Exception as e:
            last_error = e
            if attempt <= retries:
                continue
            raise RuntimeError(f"Не удалось получить валидный JSON: {e}") from e

    raise RuntimeError(f"Не удалось выполнить LLM-вызов: {last_error}")
