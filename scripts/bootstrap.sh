#!/usr/bin/env bash
set -euo pipefail

echo "==> NyayaAI bootstrap"

# Prereqs
command -v uv        >/dev/null 2>&1 || { echo "Install uv: https://docs.astral.sh/uv/"; exit 1; }
command -v pnpm      >/dev/null 2>&1 || { echo "Install pnpm: https://pnpm.io/"; exit 1; }
command -v flutter   >/dev/null 2>&1 || { echo "Install Flutter via fvm: https://fvm.app/"; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo "Install Terraform: https://developer.hashicorp.com/terraform/install"; exit 1; }
command -v go        >/dev/null 2>&1 || { echo "Install Go 1.23+"; exit 1; }

echo "==> Python services (uv sync)"
for svc in services/fairness services/orchestrator services/api services/reporter packages/fairlearn-extensions packages/india-taxonomy packages/contracts; do
  if [ -f "$svc/pyproject.toml" ]; then
    ( cd "$svc" && uv sync )
  fi
done

echo "==> Go services"
( cd services/watcher && go mod download )

echo "==> TypeScript (pnpm)"
if [ -f "services/orchestrator/evals/package.json" ]; then
  ( cd services/orchestrator/evals && pnpm install )
fi
if [ -f "apps/admin/package.json" ]; then
  ( cd apps/admin && pnpm install )
fi

echo "==> Flutter"
( cd apps/flutter && flutter pub get )

echo "==> Terraform (staging)"
( cd infra/terraform/envs/staging && terraform init -backend=false )

echo "==> Done. Run 'make test.fast' to verify."
