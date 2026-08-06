"""Pydantic request/response models for the fraud-detection API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RiskResponse(BaseModel):
    probability: float
    risk_tier: str
    action: str


class PredictRequest(BaseModel):
    """A raw IEEE-compatible transaction payload.

    ``values`` holds raw model feature values (numeric). Unknown feature
    names and missing critical fields are rejected by the feature contract.
    ``transaction_id`` makes the decision idempotent (first decision wins).
    """

    values: dict[str, float] = Field(default_factory=dict)
    transaction_id: str | None = None


class PredictResponse(RiskResponse):
    model_version: str
    transaction_id: str
    decision: Literal["APPROVE", "MANUAL_REVIEW", "DECLINE"]
    policy_version: str
    contract_version: str
    feature_report: dict[str, object]


class SimulateRequest(BaseModel):
    """Friendly, checkout-style inputs for the **demo scenario builder**.

    These are human-readable inputs mapped onto model features over a
    scenario profile. They are a demo helper, not a payment-gateway
    integration — the model still depends on the full 400-feature schema.
    """

    profile: Literal["typical", "nonfraud", "fraud"] = "typical"
    transaction_id: str | None = None
    amount: float | None = None
    card_brand: str | None = None
    billing_distance: float | None = None
    card_match_count: float | None = None
    purchase_frequency: float | None = None
    days_since_activity: float | None = None


class SimulateResponse(PredictResponse):
    profile: str
    mapped_values: dict[str, float]
    feature_usage: dict[str, object]


class BatchScoreRow(RiskResponse):
    id: str | int | None = None
    transaction_id: str | None = None
    decision: Literal["APPROVE", "MANUAL_REVIEW", "DECLINE"] | None = None
    policy_version: str | None = None
    contract_version: str | None = None


class BatchScoreResponse(BaseModel):
    model_version: str
    count: int
    rows: list[BatchScoreRow]
    errors: list[dict[str, str]] = Field(default_factory=list)


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


class ReviewOutcomeRequest(BaseModel):
    """Analyst verdict on a queued decision."""

    verdict: Literal["safe", "fraud"]
    note: str | None = None


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
