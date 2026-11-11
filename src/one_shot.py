from src.llm_client import chat_json
from src.models import ReviewAnalysis
from src.prompts import ONE_SHOT_SYSTEM, ONE_SHOT_USER


def analyze_one_shot(review_text: str) -> tuple[ReviewAnalysis, int]:
    llm = chat_json(
        ONE_SHOT_SYSTEM,
        ONE_SHOT_USER.format(review_text=review_text),
    )
    tokens = llm.usage["total_tokens"] if llm.usage else 0
    return ReviewAnalysis(**llm.data), tokens
