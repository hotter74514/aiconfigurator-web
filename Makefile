SHELL := /bin/sh
PACKAGE_MANAGER ?= npm
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
AICONFIGURATOR_IMAGE ?= aiconfigurator-web:local
AICONFIGURATOR_MODEL ?= Qwen/Qwen3-32B-FP8
AICONFIGURATOR_GPUS ?= 32
AICONFIGURATOR_SYSTEM ?= h200_sxm

.PHONY: help status docs check smoke-configurator docker-build minikube-load-image container-check k8s-render dev build format lint typecheck test ci

PORTAL_IMAGE ?= aiconfigurator-portal:local
PORTAL_PLATFORM ?= linux/amd64

help:
	@echo "Available targets:"
	@echo "  make status    Show the current Git branch and working tree"
	@echo "  make check     Validate project guidance and configured app checks"
	@echo "  make smoke-configurator  Run the Linux/amd64 AIConfigurator smoke test"
	@echo "  make docker-build       Build the Linux/amd64 portal image"
	@echo "  make minikube-load-image Load the portal image into the Minikube profile"
	@echo "  make container-check    Check portal probes and metrics in Docker"
	@echo "  make k8s-render         Render local Kubernetes manifests"
	@echo "  make dev       Start the configured development server"
	@echo "  make build     Create the production build"
	@echo "  make format    Run the configured formatter"
	@echo "  make lint      Run the configured linter"
	@echo "  make typecheck Run the configured type checker"
	@echo "  make test      Run the configured test suite"
	@echo "  make ci        Run checks and the production build"

status:
	@git status --short --branch

docs:
	@test -f AGENTS.md
	@test -f ARCHITECTURE.md
	@test -f DEVELOPMENT.md
	@test -f ROADMAP.md
	@test -f TASKS.md
	@test -d prompts
	@test -f .codex/config.toml
	@test -f docs/assignment-brief.md
	@test -f docs/task-000-smoke-test.md
	@test -f docs/task-001-cli-artifacts.md
	@test -f docs/task-015-worker.md
	@test -f docs/task-016-results.md
	@test -f docs/task-017-artifacts.md
	@test -f docs/task-020-form.md
	@test -f docs/task-021-polling.md
	@test -f docs/task-022-results.md
	@test -f docs/task-030-backpressure.md
	@test -f docs/task-031-timeout-cancellation.md
	@test -f docs/task-032-probes.md
	@test -f docs/task-033-observability.md
	@test -f docs/task-034-logging.md
	@test -f docs/task-040-container.md
	@test -f docs/task-052-clean-checkout.md
	@test -f docs/task-053-demo-rehearsal.md
	@test -f docs/task-054-commit-history.md
	@test -f docs/task-055-pareto.md
	@test -x scripts/container-check.sh
	@test -f k8s/kustomization.yaml
	@test -f k8s/deployment.yaml
	@test -f k8s/service.yaml
	@test -f templates/form.html
	@test -f pyproject.toml
	@test -f app/main.py
	@test -f tests/test_runs_api.py
	@test -f docs/DESIGN_DECISIONS.md
	@test -f docs/local-observability.md
	@test -f docs/decisions/012-local-observability-stack.md
	@test -f docs/demo-checklist.md
	@test -f docs/decisions/001-execution-model.md
	@test -f docs/decisions/002-api-model.md
	@test -f docs/decisions/003-aiconfigurator-integration.md
	@test -f docs/decisions/004-artifact-storage.md
	@test -f docs/decisions/005-concurrency.md
	@test -f docs/decisions/006-probes.md
	@test -f docs/decisions/007-observability.md
	@test -f docs/decisions/008-caching.md
	@test -f docs/decisions/009-multi-tenancy.md
	@test -f docs/decisions/010-output-trust.md
	@test -f docs/decisions/011-timeout-cancellation.md
	@test -f docs/decisions/013-loki-alloy-log-forwarding.md

smoke-configurator:
	AICONFIGURATOR_IMAGE=$(AICONFIGURATOR_IMAGE) \
	AICONFIGURATOR_MODEL=$(AICONFIGURATOR_MODEL) \
	AICONFIGURATOR_GPUS=$(AICONFIGURATOR_GPUS) \
	AICONFIGURATOR_SYSTEM=$(AICONFIGURATOR_SYSTEM) \
	./scripts/smoke-test.sh

docker-build:
	docker build --platform $(PORTAL_PLATFORM) --provenance=false --sbom=false --target runtime --load -t $(PORTAL_IMAGE) .

minikube-load-image: docker-build
	./scripts/minikube-load-image.sh $(PORTAL_IMAGE)

container-check: docker-build
	PORTAL_IMAGE=$(PORTAL_IMAGE) PORTAL_PLATFORM=$(PORTAL_PLATFORM) ./scripts/container-check.sh

k8s-render:
	kubectl kustomize k8s

check: docs
	@if test -f package.json; then \
		$(MAKE) lint typecheck test; \
	elif test -f pyproject.toml; then \
		$(PYTHON) -m pytest; \
	else \
		echo "Scaffold checks passed; application package is not configured yet."; \
	fi

dev:
	@if test -f package.json; then \
		$(PACKAGE_MANAGER) run dev; \
	elif test -f pyproject.toml; then \
		$(PYTHON) -m uvicorn app.main:app --reload; \
	else \
		echo "Application package is not configured yet; choose the application stack first."; exit 1; \
	fi

build:
	@if test -f package.json; then \
		$(PACKAGE_MANAGER) run build; \
	elif test -f pyproject.toml; then \
		$(MAKE) docker-build; \
	else \
		echo "Application package is not configured yet; choose the application stack first."; exit 1; \
	fi

format:
	@test -f package.json || (echo "package.json is not configured yet; configure a formatter first."; exit 1)
	$(PACKAGE_MANAGER) run format

lint:
	@test -f package.json || (echo "package.json is not configured yet; configure a linter first."; exit 1)
	$(PACKAGE_MANAGER) run lint

typecheck:
	@test -f package.json || (echo "package.json is not configured yet; configure type checking first."; exit 1)
	$(PACKAGE_MANAGER) run typecheck

test:
	@if test -f package.json; then \
		$(PACKAGE_MANAGER) test; \
	elif test -f pyproject.toml; then \
		$(PYTHON) -m pytest; \
	else \
		echo "Tests are not configured yet."; exit 1; \
	fi

ci: check
	@if test -f package.json; then \
		$(MAKE) build; \
	elif test -f pyproject.toml; then \
		$(MAKE) docker-build; \
	else \
		echo "Application build is not configured yet."; \
	fi
