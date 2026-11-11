from typing import List, Literal
from pydantic import BaseModel, Field


class AspectRaw(BaseModel):
    name: str = Field(description="Краткое название аспекта, например 'доставка'")
    quote: str = Field(description="Цитата из отзыва, где упомянут аспект")


class ExtractionResult(BaseModel):
    aspects: List[AspectRaw] = Field(default_factory=list)


class Aspect(BaseModel):
    name: str
    sentiment: Literal["positive", "negative", "neutral"]
    evidence: str


class ReviewAnalysis(BaseModel):
    overall_sentiment: Literal["positive", "negative", "neutral", "mixed"]
    aspects: List[Aspect] = Field(default_factory=list)
    summary: str
    business_recommendation: str
