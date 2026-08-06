"""Capture demo screenshots of the web console for the README.

Requires the API to be running (``uvicorn api.main:app``) and Playwright
with Chromium installed (``pip install playwright && python -m playwright
install chromium``).

Usage:
    python scripts/capture_screenshots.py [--base http://localhost:8000]

Writes PNGs into ``docs/screenshots/``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"


def _set_sim(page, profile: str, values: dict[str, str]) -> None:
    page.select_option("#sim-profile", profile)
    for name, value in values.items():
        if name == "card_brand":
            page.select_option(f"#sim-fields select[name='{name}']", value)
        else:
            page.fill(f"#sim-fields input[name='{name}']", value)


def capture(base: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda e: print("PAGE ERROR:", e))
        page.on("console", lambda m: print("CONSOLE:", m.type, m.text))

        # --- Score tab: checkout-style fraudulent case ---
        page.goto(base, wait_until="networkidle")
        page.wait_for_selector("#sim-fields input[name='amount']", timeout=20000)
        _set_sim(
            page,
            "fraud",
            {
                "amount": "840",
                "card_brand": "amex",
                "billing_distance": "0",
                "card_match_count": "12",
                "purchase_frequency": "44",
                "days_since_activity": "120",
            },
        )
        page.click("#sim-btn")
        page.wait_for_function(
            "() => document.querySelector('#result') && !document.querySelector('#result').classList.contains('hidden') && document.querySelector('#summary-text').innerText.length > 0",
            timeout=20000,
        )
        page.wait_for_timeout(500)
        page.screenshot(path=OUT_DIR / "score-checkout.png", full_page=True)

        # --- Batch tab: empty upload state ---
        page.click(".tab[data-tab='batch']")
        page.wait_for_selector("#dropzone")
        page.screenshot(path=OUT_DIR / "batch-upload.png", full_page=True)

        # --- Batch tab: scored results ---
        sample = Path(__file__).resolve().parents[1] / "web" / "sample_transactions.csv"
        page.set_input_files("#batch-file", str(sample))
        page.click("#batch-btn")
        page.wait_for_selector("#batch-result:not(.hidden)", timeout=30000)
        page.wait_for_selector("#batch-chart")
        page.screenshot(path=OUT_DIR / "batch-results.png", full_page=True)

        # --- Model tab ---
        page.click(".tab[data-tab='model']")
        page.wait_for_selector("#model-cards .kpi")
        page.screenshot(path=OUT_DIR / "model-overview.png", full_page=True)

        browser.close()
    print(f"Screenshots written to {OUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    capture(args.base)
