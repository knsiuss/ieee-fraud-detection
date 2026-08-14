"""LLM audit-report provider — free-tier / local-open-weight, with graceful
degradation and a hard no-paid-API posture.

Constraint (§1.2 of the feature spec): no budget for paid APIs. Two options
were considered:

* (a) free-tier-hosted commercial API (e.g. a provider's free tier) — fine
  until the free quota is exhausted; the provider here fails safe when the
  call fails (→ template report), so an exhausted budget degrades, it does
  not break.
* (b) local / open-weight model via any **OpenAI-compatible** endpoint
  (Ollama, LM Studio, llama.cpp server) — recommended for this repo: no
  keys, no quota, runs on the existing CPU; latency is the only cost, and
  report generation is already async/decoupled from the scoring path.

Trade-off stated: local models are a narration-quality compromise and add
CPU load on cold start, but they honour the no-paid-API constraint and the
single-process architecture. The implementation therefore uses an
OpenAI-compatible ``/v1/chat/completions`` request pointed at whatever base
URL is configured, and **returns ``None`` on any failure** so the caller
falls back to the deterministic template report (``audit_report.py``).

Settings are centralised in :mod:`fraud_detect.config` and are resolved at
**call time** (never frozen at import), so operators can override them via
the documented env vars and tests can monkeypatch ``config`` attributes.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from fraud_detect import config


def llm_enabled() -> bool:
    return bool(config.LLM_BASE_URL)


def generate_llm(context: dict[str, Any]) -> str | None:
    """Ask the configured LLM to narrate the report context.

    Returns the raw text response, or ``None`` if the LLM is not configured
    or the call fails (timeout, HTTP error, network) — the caller then falls
    back to the deterministic template report.
    """
    base_url = config.LLM_BASE_URL
    if not base_url:
        return None
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a fraud-analysis report writer. Follow the user's "
                    "instructions exactly; output valid JSON only."
                ),
            },
            {"role": "user", "content": _prompt(context)},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            **({"Authorization": f"Bearer {config.LLM_API_KEY}"} if config.LLM_API_KEY else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.LLM_TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return content if isinstance(content, str) and content.strip() else None
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, KeyError, ValueError):
        return None


def _prompt(context: dict[str, Any]) -> str:
    """Delegated to audit_report.build_prompt via a thin re-export contract.

    Kept synchronous-simple; called from store.generate_audit_report inside
    ``asyncio.to_thread`` so it never blocks the request/response cycle.
    """
    from fraud_detect.audit_report import build_prompt

    return build_prompt(context)
