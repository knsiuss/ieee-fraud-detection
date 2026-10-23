"""Sphinx configuration for the Sentinel fraud-detection docs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent

project = "Sentinel — Fraud Detection"
author = "Sentinel contributors"
copyright = "2026, Sentinel contributors"

extensions = ["myst_parser", "sphinx_copybutton"]
myst_enable_extensions = ["colon_fence", "deflist", "fieldlist", "tasklist"]
myst_heading_anchors = 3
# Code fences in the docs use mermaid/cron/json-with-ellipsis; Pygments
# cannot lex those, and the fallback rendering is intentional.
suppress_warnings = ["myst.xref_missing", "myst.header", "misc.highlighting_failure"]

html_theme = "furo"
html_title = project
html_baseurl = "/"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
