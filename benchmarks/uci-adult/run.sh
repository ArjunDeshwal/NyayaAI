#!/usr/bin/env bash
# Fetch UCI Adult, train a blind baseline model, and run the full NyayaAI
# fairness audit on the resulting parquet.
#
# Requires: uv workspace sync'd. From repo root:
#   uv sync && bash benchmarks/uci-adult/run.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${HERE}"

mkdir -p data artifacts

uv run python fetch.py --out data/adult.parquet --seed 42

uv run python -m nyayai_fairness.cli audit data/adult.parquet \
  --protected sex,race \
  --outcome income_high \
  --model-score model_score \
  --threshold 0.5 \
  --seed 42 \
  --min-slice-n 30 \
  --report-out artifacts/report.json

echo "Report written to ${HERE}/artifacts/report.json"
