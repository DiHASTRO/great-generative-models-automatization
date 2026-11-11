import json

from pydantic import ValidationError

from src.llm_client import chat_json
from src.models import ExtractionResult, ReviewAnalysis
from src.prompts import (
    EXTRACT_SYSTEM,
    EXTRACT_USER,
    CLASSIFY_SYSTEM,
    CLASSIFY_USER,
)


def analyze_workflow(review_text: str) -> tuple[ReviewAnalysis, int]:
    total_tokens = 0

    try:
        llm1 = chat_json(
            EXTRACT_SYSTEM,
            EXTRACT_USER.format(review_text=review_text),
        )
        if llm1.usage:
            total_tokens += llm1.usage["total_tokens"]
        extracted = ExtractionResult(**llm1.data)
    except (RuntimeError, ValidationError, TypeError):
        extracted = ExtractionResult(aspects=[])

    aspects_json = json.dumps(
        [a.model_dump() for a in extracted.aspects],
        ensure_ascii=False,
        indent=2,
    )
    llm2 = chat_json(
        CLASSIFY_SYSTEM,
        CLASSIFY_USER.format(review_text=review_text, aspects_json=aspects_json),
    )
    if llm2.usage:
        total_tokens += llm2.usage["total_tokens"]

    return ReviewAnalysis(**llm2.data), total_tokens
