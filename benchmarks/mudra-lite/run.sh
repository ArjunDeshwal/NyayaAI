#!/usr/bin/env bash
# Regenerate MUDRA-Lite and run the full NyayaAI fairness audit on it.
#
# Requires: uv workspace sync'd. From repo root:
#   uv sync && bash benchmarks/mudra-lite/run.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${HERE}"

mkdir -p data artifacts

python generate.py --out data/mudra-lite.parquet --n 10000 --seed 42

python -m nyayai_fairness.cli audit data/mudra-lite.parquet \
  --protected caste_disclosed,gender,habitation \
  --outcome approved \
  --model-score model_score \
  --report-out artifacts/report.json

echo "Report written to ${HERE}/artifacts/report.json"
