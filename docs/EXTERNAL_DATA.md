# External-data validation — research & comparability

## Status

**No external validation has been run.** This document records the research
and comparability analysis so the decision is transparent and reproducible.
Running actual external validation would require downloading datasets under
their own terms and a schema-mapping study — see *Blocked / needs action*.

> Integrity note: the web-search tool returned no results during this
> research pass, so the table below is based on widely-documented public
> knowledge (dataset landing pages / papers cited inline). **Re-verify current
> license terms and URLs before using any of these datasets.**

## Candidate public fraud datasets

| Dataset | Source / licence | Rows | Schema | Comparability to IEEE-CIS |
|---|---|---|---|---|
| **IEEE-CIS Fraud Detection** (in use) | [Kaggle](https://www.kaggle.com/c/ieee-fraud-detection), Vesta; Kaggle competition terms | ~590K labeled | 400+ raw features (`card*`, `C*`, `D*`, `V*`, `id_*`) + temporal `TransactionDT` | — (this project's data) |
| **Credit Card Fraud Detection** (`creditcard.csv`) | [Kaggle](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud); **CC BY-NC-SA 4.0** (non-commercial, share-alike) | 284,807 | 28 **PCA-transformed** features (`V1`–`V28`) + `Time` + `Amount` | **Incompatible feature space** — PCA components have no column mapping to IEEE-CIS raw features. Cannot merge. |
| **PaySim** (synthetic mobile-money fraud) | UCI ML Repo; **CC BY 4.0** | ~6.4M transactions | `type`, `amount`, `old/newbalance`, no card/device/identity | Incompatible schema and different domain (mobile wallet). Cannot merge. |
| **Bank Account Fraud (BAF)** | Open research dataset (bank account opening fraud) | ~1M | account-opening fields | Different entity and label semantics (account fraud vs transaction fraud). Not comparable without careful relabeling; not merged. |

## Comparability analysis

- IEEE-CIS features are dominated by **anonymised Vesta features (`V*`)** and
  card-count/time-delta features with no public dictionary. No other public
  dataset shares that feature space, so **direct transfer learning or
  dataset concatenation is not defensible**.
- Label semantics differ across datasets (card-payment fraud vs mobile-money
  fraud vs account-opening fraud). Merging labels would violate the
  "do not blindly merge incompatible datasets or labels" rule.

## What *would* be defensible (documented, not done)

- **Isolated drift analysis**: score transactions from another card-payment
  dataset (e.g. `creditcard.csv` under its licence) through the trained model
  and report the prediction distribution vs the IEEE-CIS training
  distribution — as a *drift* signal, **not** as a performance claim
  (feature-space incompatibility means scores are not directly meaningful).
- **Documented failure analysis** on the above, clearly labelled as
  non-comparable.

## Blocked / needs action

- Downloading and validating `creditcard.csv` / PaySim / BAF requires
  accepting their licence terms and, for Kaggle, a Kaggle account.
  **Credentials are needed** for Kaggle downloads — none are provided or
  stored in this repo (and none should be).
- If you want an external-validation experiment, tell me which dataset and
  whether you have (or can create) the credentials; I will then add a
  versioned, schema-mapped experiment script and report it honestly — or
  mark it blocked if terms prohibit use.

## Decisions taken

1. **No dataset merging** — schemas and label semantics are incompatible.
2. **No external metrics reported** — there are none; nothing was run.
3. External validation is tracked as **blocked / future work**, not "done".
