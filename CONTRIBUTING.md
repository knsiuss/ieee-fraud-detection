# Contributing

This is a personal portfolio project. Issues and suggestions are welcome,
but active development is done by the author.

## Setup

```bash
pip install -e ".[lgbm,dev]"
pre-commit install
make lint
make test
```

## Code conventions

- Type hints required for all function signatures
- Google-style docstrings with examples
- No `print()` — use `logging` instead
- Prefer vectorised pandas/numpy operations over `.apply()` or loops

## PRs

Not actively monitored, but feel free to open one.
