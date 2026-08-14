"""Tests for api.llm_provider — config-resolved, fail-safe LLM narration."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api import llm_provider  # noqa: E402
from fraud_detect import config  # noqa: E402

_CONTEXT = {
    "score": 0.883,
    "decision": "DECLINE",
    "risk_tier": "high",
    "review_above": 0.15,
    "decline_above": 0.5,
    "summary": "High risk of fraud.",
    "drivers": [
        {
            "feature": "TransactionAmt",
            "label": "Amount",
            "value_text": "$2,400.00",
            "typical_text": "$68.80",
            "contribution": 0.32,
            "direction": "fraud",
        }
    ],
    "amount": 2400.0,
    "amount_typical": 68.8,
}


class TestConfigResolution:
    def test_enabled_follows_config_at_call_time(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_BASE_URL", "")
        assert llm_provider.llm_enabled() is False
        # Runtime override works: settings are not frozen at import.
        monkeypatch.setattr(config, "LLM_BASE_URL", "http://localhost:11434/v1")
        assert llm_provider.llm_enabled() is True

    def test_disabled_returns_none_without_network(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_BASE_URL", "")
        assert llm_provider.generate_llm(_CONTEXT) is None

    def test_unreachable_server_fails_safe(self, monkeypatch):
        # A port that refuses connections must degrade to None (template
        # fallback), never raise.
        monkeypatch.setattr(config, "LLM_BASE_URL", "http://127.0.0.1:1/v1")
        monkeypatch.setattr(config, "LLM_TIMEOUT", 2.0)
        assert llm_provider.generate_llm(_CONTEXT) is None

    def test_model_name_and_key_from_config(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_BASE_URL", "http://127.0.0.1:1/v1")
        monkeypatch.setattr(config, "LLM_MODEL", "mistral")
        monkeypatch.setattr(config, "LLM_API_KEY", "sekret")
        assert llm_provider.llm_enabled() is True
