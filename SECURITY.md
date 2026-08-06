# Security Policy

This is a **portfolio / demonstration** project, not a production fraud
system. It does not handle real card, identity, or payment data.

## Reporting a vulnerability

- **Do not** open a public issue for a live exploit detail.
- Email the repository author (see `LICENSE` / GitHub profile) with a clear
  description, reproduction steps, and impact.
- Private disclosures can also be sent via a GitHub private advisory
  (Security tab) if you prefer.

## Scope

- The FastAPI service in `api/`, the web UI in `web/`, and the Python package
  in `src/`.
- The retrain endpoint is protected by `X-Admin-Key` **only when
  `FRAUD_API_ADMIN_KEY` is set** — set it before any public deployment.
- Rate limiting is per-process and demo-grade (see `docs/DEPLOYMENT.md`).

## What is never acceptable

- Committing secrets, credentials, or private/live data to the repository.
- Wiring this code to a real payment gateway or real fraud-decision
  workflow — it is explicitly a demo.

## No bug bounty

Personal project; there is no reward program.
