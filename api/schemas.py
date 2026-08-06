"""Pydantic request/response models for the fraud-detection API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """A single transaction to score.

    ``values`` holds the feature values the analyst provided; every feature
    left out falls back to the median seen at training time.
    """

    values: dict[str, float] = Field(default_factory=dict)


class RiskResponse(BaseModel):
    probability: float
    risk_tier: str
    action: str


class PredictResponse(RiskResponse):
    model_version: str


class SimulateRequest(BaseModel):
    """Friendly, checkout-style inputs for the transaction simulator."""

    profile: Literal["typical", "nonfraud", "fraud"] = "typical"
    amount: float | None = None
    card_brand: str | None = None
    billing_distance: float | None = None
    card_match_count: float | None = None
    purchase_frequency: float | None = None
    days_since_activity: float | None = None


class SimulateResponse(PredictResponse):
    profile: str
    mapped_values: dict[str, float]


class BatchScoreRow(RiskResponse):
    id: str | int | None = None
    values: dict[str, float]


class BatchScoreResponse(BaseModel):
    model_version: str
    count: int
    rows: list[BatchScoreRow]


class ShapFeature(BaseModel):
    feature: str
    contribution: float
    direction: Literal["fraud", "safe"]


class Driver(BaseModel):
    feature: str
    label: str
    value: float | None
    typical: float | None
    value_text: str
    typical_text: str
    contribution: float
    direction: Literal["fraud", "safe"]


class ExplainResponse(BaseModel):
    probability: float
    risk_tier: str
    action: str
    model_version: str
    summary: str
    drivers: list[Driver]
    features: list[ShapFeature]


class FeedbackRequest(BaseModel):
    values: dict[str, float] = Field(default_factory=dict)
    verdict: Literal[0, 1, "fraud", "safe"] = Field(
        ...,
        description="Analyst label: 0/1 or 'safe'/'fraud'.",
    )


class FeedbackResponse(BaseModel):
    accepted: bool
    pool_size: int


class RetrainResponse(BaseModel):
    swapped: bool
    old_auc: float
    new_auc: float
    old_version: str
    feedback_rows: int
    reason: str


class HealthResponse(BaseModel):
    status: str
    model_present: bool
    model_version: str | None = None
