SHELL := /bin/sh
PACKAGE_MANAGER ?= npm
AICONFIGURATOR_IMAGE ?= aiconfigurator-web:local
AICONFIGURATOR_MODEL ?= Qwen/Qwen3-32B-FP8
AICONFIGURATOR_GPUS ?= 32
AICONFIGURATOR_SYSTEM ?= h200_sxm

.PHONY: help status docs check smoke-configurator dev build format lint typecheck test ci

help:
	@echo "Available targets:"
	@echo "  make status    Show the current Git branch and working tree"
	@echo "  make check     Validate project guidance and configured app checks"
	@echo "  make smoke-configurator  Run the Linux/amd64 AIConfigurator smoke test"
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
	@test -f docs/DESIGN_DECISIONS.md
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

smoke-configurator:
	AICONFIGURATOR_IMAGE=$(AICONFIGURATOR_IMAGE) \
	AICONFIGURATOR_MODEL=$(AICONFIGURATOR_MODEL) \
	AICONFIGURATOR_GPUS=$(AICONFIGURATOR_GPUS) \
	AICONFIGURATOR_SYSTEM=$(AICONFIGURATOR_SYSTEM) \
	./scripts/smoke-test.sh

check: docs
	@if test -f package.json; then \
		$(MAKE) lint typecheck test; \
	else \
		echo "Scaffold checks passed; package.json is not configured yet."; \
	fi

dev:
	@test -f package.json || (echo "package.json is not configured yet; choose the application stack first."; exit 1)
	$(PACKAGE_MANAGER) run dev

build:
	@test -f package.json || (echo "package.json is not configured yet; choose the application stack first."; exit 1)
	$(PACKAGE_MANAGER) run build

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
	@test -f package.json || (echo "package.json is not configured yet; configure tests first."; exit 1)
	$(PACKAGE_MANAGER) test

ci: check
	@if test -f package.json; then \
		$(MAKE) build; \
	else \
		echo "Scaffold CI checks passed; application build is not configured yet."; \
	fi
