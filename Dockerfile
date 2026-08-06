# IEEE-CIS Fraud Detection — FastAPI service image.
#
# Builds a self-contained image: installs deps, copies the app, and bootstraps
# a serving model from the committed sample (dashboard/data/sample.parquet) so
# the container responds immediately. Bake a real model by placing the trained
# artefact in data/models/current before building, or retrain at runtime.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    FRAUD_DETECT_DATA_ROOT=/app/data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY api ./api
COPY web ./web
COPY scripts ./scripts
COPY dashboard/data ./dashboard/data
COPY data/metadata ./data/metadata

# Bootstrap model from the committed sample (skips cleanly if a model is baked).
RUN python scripts/train_model.py || echo "bootstrap model not built (using baked artefact)"

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
