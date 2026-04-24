FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_NO_SYNC=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpango-1.0-0 libpangoft2-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY packages /app/packages
COPY services /app/services

RUN uv pip install --system \
      /app/packages/contracts \
      /app/packages/india-taxonomy \
      /app/packages/fairlearn-extensions \
      /app/services/fairness \
      '/app/services/orchestrator[vertex]' \
      /app/services/reporter \
      '/app/services/api[test]' \
      && uv pip install --system weasyprint

ENV NYAYAI_LLM_BACKEND=stub \
    NYAYAI_API_ARTIFACTS_DIR=/tmp/nyayai-artifacts \
    PORT=8080

EXPOSE 8080

CMD ["uvicorn", "nyayai_api:app", "--host", "0.0.0.0", "--port", "8080"]
