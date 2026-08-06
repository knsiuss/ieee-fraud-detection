"""Checkout-style transaction simulator for the review console.

Maps a small set of human-readable transaction fields (amount, card brand,
billing distance, card match count, purchase frequency, days since last
activity) onto the model's numeric feature space. The overlay is applied on
top of a **profile baseline** — the training median of a segment stored in
the artefact (``typical`` / ``nonfraud`` / ``fraud``) — so fields the user
does not edit default to realistic segment statistics instead of a plain
global median.

Everything here is deterministic and documented; ``FIELD_FEATURE_MAP`` and
``CARD_BRANDS`` are the single source of truth for how friendly inputs
become model features.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .serving import align_features

#: Card brand -> feature values the model knows. ``card1`` is the anonymised
#: issuer code, ``card3`` the card-network count.
CARD_BRANDS: dict[str, dict[str, float]] = {
    "visa": {"card1": 6200.0, "card3": 2.0},
    "mastercard": {"card1": 5300.0, "card3": 2.0},
    "amex": {"card1": 3700.0, "card3": 3.0},
    "discover": {"card1": 6500.0, "card3": 2.0},
}

#: Friendly field -> model feature (numeric fields only).
FIELD_FEATURE_MAP: dict[str, str] = {
    "amount": "TransactionAmt",
    "billing_distance": "dist1",
    "card_match_count": "C1",
    "purchase_frequency": "C13",
    "days_since_activity": "D1",
}

#: Schema exposed to the UI via ``GET /api/sim/fields``.
FRIENDLY_FIELDS: list[dict[str, Any]] = [
    {
        "name": "amount",
        "label": "Transaction amount (USD)",
        "type": "number",
        "min": 0,
        "max": 3000,
        "value": 120,
        "feature": "TransactionAmt",
    },
    {
        "name": "card_brand",
        "label": "Card brand",
        "type": "select",
        "options": list(CARD_BRANDS),
        "feature": None,
    },
    {
        "name": "billing_distance",
        "label": "Distance from billing (km)",
        "type": "number",
        "min": 0,
        "max": 500,
        "value": 10,
        "feature": "dist1",
    },
    {
        "name": "card_match_count",
        "label": "Accounts linked to the card",
        "type": "number",
        "min": 1,
        "max": 100,
        "value": 1,
        "feature": "C1",
    },
    {
        "name": "purchase_frequency",
        "label": "Purchase frequency",
        "type": "number",
        "min": 1,
        "max": 200,
        "value": 2,
        "feature": "C13",
    },
    {
        "name": "days_since_activity",
        "label": "Days since last card activity",
        "type": "number",
        "min": 0,
        "max": 600,
        "value": 0,
        "feature": "D1",
    },
]

#: Named profile baselines a simulator run can start from.
PROFILES: list[str] = ["typical", "nonfraud", "fraud"]


def map_friendly(inputs: dict[str, Any]) -> dict[str, float]:
    """Map friendly inputs to model feature values (numeric fields + brand)."""
    out: dict[str, float] = {}
    for field, feature in FIELD_FEATURE_MAP.items():
        if inputs.get(field) is not None:
            out[feature] = float(inputs[field])
    brand = inputs.get("card_brand")
    if brand in CARD_BRANDS:
        out.update(CARD_BRANDS[brand])
    return out


def build_row(
    inputs: dict[str, Any],
    features: list[str],
    baseline: pd.DataFrame,
    profiles: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Build an aligned feature row from friendly inputs over a profile median."""
    profile = inputs.get("profile", "typical")
    base = (profiles or {}).get(profile) if profiles else None
    if base is None:
        base = baseline
    row = base.copy()
    for feature, value in map_friendly(inputs).items():
        if feature in row.columns:
            row.loc[0, feature] = value
    return align_features(row, features)
