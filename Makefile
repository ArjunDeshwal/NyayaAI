.PHONY: help bootstrap lint test test.fast test.ui test.int benchmark benchmark.% eval fmt clean deploy.staging deploy.prod api.dev api.docker

help:
	@echo "NyayaAI — common commands:"
	@echo "  make bootstrap          Install all deps (Python, TS, Flutter, Terraform)"
	@echo "  make lint               Run all linters"
	@echo "  make fmt                Auto-format all code"
	@echo "  make test               Full test suite"
	@echo "  make test.fast          Unit tests only"
	@echo "  make test.ui            Flutter widget + integration tests"
	@echo "  make test.int           Integration tests (Firebase Emulator)"
	@echo "  make benchmark          Run all benchmarks (UCI Adult, COMPAS, MUDRA-Lite, etc.)"
	@echo "  make benchmark.<name>   Run a single benchmark"
	@echo "  make eval               Genkit agent evals (TS)"
	@echo "  make clean              Remove build artifacts"
	@echo "  make api.dev            Run API locally with uvicorn (stub LLM backend)"
	@echo "  make api.docker         Build the API container"
	@echo "  make deploy.staging     Deploy to staging"
	@echo "  make deploy.prod        Deploy to prod (requires approval)"

bootstrap:
	./scripts/bootstrap.sh

lint:
	cd services/fairness && uv run ruff check . && uv run pyright
	cd services/orchestrator && uv run ruff check . && uv run pyright
	cd services/api && uv run ruff check . && uv run pyright
	cd services/reporter && uv run ruff check . && uv run pyright
	cd services/watcher && go vet ./... && gofmt -l .
	cd apps/flutter && dart analyze
	cd services/orchestrator/evals && pnpm lint
	cd infra/terraform && terraform fmt -check -recursive

fmt:
	cd services/fairness && uv run ruff format .
	cd services/orchestrator && uv run ruff format .
	cd services/api && uv run ruff format .
	cd services/reporter && uv run ruff format .
	cd services/watcher && gofmt -w .
	cd apps/flutter && dart format lib test
	cd infra/terraform && terraform fmt -recursive

test: lint test.fast test.int test.ui eval

test.fast:
	cd services/fairness && uv run pytest -q
	cd services/orchestrator && uv run pytest -q
	cd services/api && uv run pytest -q
	cd services/reporter && uv run pytest -q
	cd services/watcher && go test ./...
	cd packages/fairlearn-extensions && uv run pytest -q

test.ui:
	cd apps/flutter && flutter test

test.int:
	./scripts/start-emulators.sh
	cd services/api && uv run pytest -q tests/integration
	./scripts/stop-emulators.sh

benchmark: benchmark.uci-adult benchmark.compas benchmark.obermeyer-repro benchmark.mudra-lite benchmark.indian-bhed

benchmark.%:
	cd benchmarks/$* && ./run.sh

eval:
	cd services/orchestrator && PYTHONPATH=src NYAYAI_LLM_BACKEND=stub python3 evals/run_evals.py --backend stub
	cd services/orchestrator/evals && pnpm run eval

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +
	find . -type d -name node_modules -prune -exec rm -rf {} +
	find . -type d -name .dart_tool -prune -exec rm -rf {} +
	find . -type d -name build -not -path "*/node_modules/*" -prune -exec rm -rf {} +

api.dev:
	NYAYAI_LLM_BACKEND=stub uv run --package nyayai-api uvicorn nyayai_api:app --reload --port 8080

api.docker:
	docker build -f services/api/Dockerfile -t nyayai-api:local .

deploy.staging:
	./scripts/deploy.sh staging

deploy.prod:
	./scripts/deploy.sh prod
