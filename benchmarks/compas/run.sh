#!/usr/bin/env bash
# Fetch ProPublica COMPAS two-year recidivism data and run the NyayaAI
# fairness audit treating the proprietary COMPAS ``decile_score`` as the
# predictor. ProPublica convention: ``decile_score >= 5`` is "medium or
# high risk" = positive prediction; ``two_year_recid`` is the ground-truth
# outcome.
#
# Requires: uv workspace sync'd. From repo root:
#   uv sync && bash benchmarks/compas/run.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${HERE}"

mkdir -p data artifacts

uv run python fetch.py --out data/compas.parquet --seed 42

uv run python -m nyayai_fairness.cli audit data/compas.parquet \
  --protected race,sex \
  --outcome two_year_recid \
  --model-score decile_score_normalized \
  --threshold 0.5 \
  --seed 42 \
  --min-slice-n 100 \
  --report-out artifacts/report.json

echo "Report written to ${HERE}/artifacts/report.json"
