# IEEE-CIS Fraud Detection — FastAPI service + React SPA image for Hugging Face Spaces.
#
# Stage 1: Build the React frontend SPA
FROM node:20-slim AS frontend-build
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm ci || npm install
COPY web/ ./
RUN npm run build

# Stage 2: Python FastAPI backend service
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    FRAUD_DETECT_DATA_ROOT=/app/data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY api ./api
COPY scripts ./scripts
COPY dashboard/data ./dashboard/data
COPY data/metadata ./data/metadata
COPY web/sample_transactions.csv ./web/sample_transactions.csv

# Copy compiled React frontend assets from Stage 1
COPY --from=frontend-build /web/dist ./web/dist

# Bootstrap model from the committed sample (skips cleanly if a model is baked).
RUN python scripts/train_model.py || echo "bootstrap model not built (using baked artefact)"

EXPOSE 7860
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
