# Configuration file for the Sphinx documentation builder.

import sys
from pathlib import Path

# Ensure the package is importable.
SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC))

project = "fraud_detect"
copyright = "2026, P. Kanisius Bagaskara"
author = "P. Kanisius Bagaskara"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "sphinx_copybutton",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
