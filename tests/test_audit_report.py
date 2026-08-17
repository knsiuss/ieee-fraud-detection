"""Tests for fraud_detect.audit_report — LLM-narrated audit reports."""

from __future__ import annotations

from fraud_detect.audit_report import (
    AI_FOOTER,
    LLM_KEYS,
    build_prompt,
    build_report,
    build_report_context,
    build_template_report,
    parse_llm_response,
)

RECORD = {
    "transaction_id": "tx-1",
    "score": 0.883,
    "decision": "DECLINE",
    "risk_tier": "high",
    "model_version": "2026-08-06T08:15",
    "policy_version": "v1",
    "thresholds": {"review_above": 0.15, "decline_above": 0.5},
    "reason_codes": [
        {
            "feature": "TransactionAmt",
            "label": "Amount",
            "value_text": "$2,400.00",
            "typical_text": "$68.80",
            "value": 2400.0,
            "typical": 68.8,
            "contribution": 0.32,
            "direction": "fraud",
        },
        {
            "feature": "C1",
            "label": "Count C1",
            "value_text": "3",
            "typical_text": "1",
            "contribution": 0.10,
            "direction": "fraud",
        },
        {
            "feature": "V258",
            "label": "V258",
            "value_text": "0.9",
            "typical_text": "0.1",
            "contribution": -0.20,
            "direction": "safe",
        },
    ],
    "summary": "High risk of fraud based on 3 elevated signals.",
}


class TestContext:
    def test_context_contains_only_allowed_fields(self):
        ctx = build_report_context(RECORD)
        assert ctx["score"] == 0.883
        assert ctx["decision"] == "DECLINE"
        assert ctx["risk_tier"] == "high"
        assert ctx["review_above"] == 0.15
        assert ctx["decline_above"] == 0.5
        assert len(ctx["drivers"]) == 3
        assert ctx["amount"] == 2400.0
        assert ctx["amount_typical"] == 68.8

    def test_context_truncates_drivers_to_five(self):
        record = dict(RECORD)
        record["reason_codes"] = [
            {"feature": f"F{i}", "label": f"F{i}", "contribution": float(i)} for i in range(10)
        ]
        ctx = build_report_context(record)
        assert len(ctx["drivers"]) == 5

    def test_no_amount_returns_none(self):
        record = dict(RECORD)
        record["reason_codes"] = [{"feature": "C1", "contribution": 1.0}]
        ctx = build_report_context(record)
        assert ctx["amount"] is None

    def test_missing_fields_get_defaults(self):
        ctx = build_report_context({})
        assert ctx["score"] == 0.0
        assert ctx["decision"] == "APPROVE"
        assert ctx["review_above"] == 0.15
        assert ctx["drivers"] == []


class TestPrompt:
    def test_prompt_injects_fields(self):
        ctx = build_report_context(RECORD)
        prompt = build_prompt(ctx)
        assert "0.8830" in prompt
        assert "DECLINE" in prompt
        assert "high" in prompt
        assert "Amount" in prompt
        assert "34.9x typical" in prompt  # 2400 / 68.8

    def test_prompt_forbids_invention(self):
        ctx = build_report_context(RECORD)
        prompt = build_prompt(ctx)
        assert "Do NOT invent facts" in prompt
        assert "NARRATE" not in prompt


class TestParse:
    def test_parses_fenced_json(self):
        text = '```json\n{"executive_summary": "ok", "risk_score": {}, "drivers": [],'
        text += ' "historical_context": "h", "recommended_action": "r"}\n```'
        parsed = parse_llm_response(text)
        assert parsed is not None
        assert parsed["executive_summary"] == "ok"

    def test_parses_bare_json_in_prose(self):
        text = (
            "Sure! Here you go: "
            '{"executive_summary": "s", "risk_score": {}, "drivers": [],'
            ' "historical_context": "h", "recommended_action": "r"} hope it helps'
        )
        assert parse_llm_response(text) is not None

    def test_garbage_returns_none(self):
        assert parse_llm_response("I am sorry, I cannot help with that.") is None
        assert parse_llm_response("") is None

    def test_missing_key_returns_none(self):
        text = (
            '{"executive_summary": "s", "risk_score": {}, "drivers": [], "historical_context": "h"}'
        )
        assert parse_llm_response(text) is None  # no recommended_action

    def test_drivers_normalised(self):
        text = (
            '{"executive_summary": "s", "risk_score": {}, "historical_context": "h",'
            ' "recommended_action": "r", "drivers": [{"feature": "F1", "narration": "n"}]}'
        )
        parsed = parse_llm_response(text)
        assert parsed["drivers"][0]["feature"] == "F1"
        assert parsed["drivers"][0]["direction"] == "safe"


class TestTemplate:
    def test_template_covers_schema_keys(self):
        ctx = build_report_context(RECORD)
        report = build_template_report(ctx)
        for key in LLM_KEYS:
            assert key in report
        assert report["risk_score"]["probability"] == 0.883
        assert len(report["drivers"]) == 3
        assert "typical" in report["drivers"][0]["narration"]

    def test_template_mentions_amount_ratio(self):
        ctx = build_report_context(RECORD)
        report = build_template_report(ctx)
        assert "34.9x" in report["historical_context"]

    def test_template_defaults_for_missing_amount(self):
        ctx = build_report_context(
            {
                "score": 0.1,
                "decision": "APPROVE",
                "risk_tier": "low",
                "thresholds": {"review_above": 0.15, "decline_above": 0.5},
            }
        )
        report = build_template_report(ctx)
        assert "not among the top drivers" in report["historical_context"]


class TestBuildReport:
    def test_llm_source_when_parsed(self):
        ctx = build_report_context(RECORD)
        text = (
            '{"executive_summary": "E", "risk_score": {"probability": 0.883},'
            ' "drivers": [], "historical_context": "H", "recommended_action": "R"}'
        )
        report, source = build_report(ctx, text, "tx-1")
        assert source == "llm"
        assert report["report_id"] == "report-tx-1"
        assert report["transaction_id"] == "tx-1"
        assert report["ai_disclaimer"] == AI_FOOTER
        assert report["executive_summary"] == "E"
        assert "model_version" in report  # identity fields are platform-owned

    def test_template_fallback_on_garbage(self):
        ctx = build_report_context(RECORD)
        report, source = build_report(ctx, "sorry, cannot do that", "tx-1")
        assert source == "template"
        assert report["ai_disclaimer"] == AI_FOOTER
        assert "executive_summary" in report

    def test_template_fallback_without_llm(self):
        ctx = build_report_context(RECORD)
        report, source = build_report(ctx, None, "tx-1")
        assert source == "template"
        assert report["ai_disclaimer"] == AI_FOOTER
