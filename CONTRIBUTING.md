# Contributing

Thanks for considering a contribution. This is a small, honest portfolio
project, so keep changes focused and backed by a real reason.

## Ground rules

- **No fabricated metrics or results.** Claims about model performance must
  be reproducible (`scripts/evaluate_model.py`) or explicitly labelled as
  future work.
- **Never commit secrets, credentials, private data, or large raw datasets.**
- Keep the demo framing: the service is a portfolio demo on public data, not
  a production fraud system.
- Respect the existing conventions (see below).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[lgbm,dev]"
pre-commit install
```

## Conventions

- **Code style**: `ruff` — `make lint` and `make format-check` must pass.
- **Tests**: `pytest` — behavior-focused; the suite must stay green
  (coverage gate 75%).
- **Commits**: one logical change per commit, conventional prefix
  (`feat(scope):`, `fix(scope):`, `docs:`, `test:`, `chore:`).
- **No decorative divider comments**; keep code self-documenting.
- New runtime features need a test; new serving logic lives in
  `fraud_detect.serving` / `fraud_detect.sim` so it is testable without the
  API.

## Workflow

1. Open an issue to discuss non-trivial changes first.
2. Branch off `main`: `git checkout -b feat/your-change`.
3. Implement with tests, run `make lint && make test`.
4. Open a pull request referencing the issue.

## Running everything

```bash
make lint          # ruff check + format check
make test          # pytest (coverage gate)
make serve         # uvicorn api.main:app --reload
```

## Reproducing the honest evaluation

```bash
python scripts/train_model.py     # train + serialise artefact
python scripts/evaluate_model.py  # random vs time-ordered split metrics
python scripts/drift_report.py    # PSI + data-quality report
```
