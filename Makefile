.PHONY: help setup install uninstall reset reset-full remove-venv reinstall \
	upgrade-deps upgrade-pd-book-tools prefetch-models \
	test test-verbose test-single test-k test-browser coverage \
	lint py-lint md-lint lint-fix py-lint-fix md-lint-fix format pre-commit-check \
	ci build clean clean-logs clean-cache clean-image-cache \
	run run-verbose run-page-timing \
	release-patch release-minor release-major _do-release

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# GPU index resolution (used by setup / install / upgrade-deps)
# ---------------------------------------------------------------------------
# `GPU` is a make var: cpu | auto | cuXXX (e.g. cu124).
# Default is auto — detect via nvidia-smi.
# `GPU=cpu` forces CPU even on a GPU box. `GPU=cu124` forces a specific tag.
GPU ?= auto

# Shell snippet that sets $$EXTRA_INDEX and $$CUDA_TAG based on $(GPU).
# Call inside a recipe with: $(_resolve_gpu_index)
define _resolve_gpu_index
	EXTRA_INDEX=""; \
	CUDA_TAG=""; \
	case "$(GPU)" in \
		cpu) \
			echo "💻 GPU=cpu — using CPU-only PyTorch."; \
			;; \
		cu*) \
			CUDA_TAG="$(GPU)"; \
			EXTRA_INDEX="https://download.pytorch.org/whl/$$CUDA_TAG"; \
			echo "🟢 GPU=$$CUDA_TAG — using PyTorch from $$EXTRA_INDEX."; \
			;; \
		auto) \
			if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then \
				CUDA_VER=$$(nvidia-smi 2>/dev/null | sed -n 's/.*CUDA Version: \([0-9]*\.[0-9]*\).*/\1/p' | head -1); \
				if [ -n "$$CUDA_VER" ]; then \
					CUDA_TAG="cu$$(echo "$$CUDA_VER" | tr -d '.')"; \
					EXTRA_INDEX="https://download.pytorch.org/whl/$$CUDA_TAG"; \
					echo "🟢 Detected CUDA $$CUDA_VER — using PyTorch with $$CUDA_TAG support."; \
				else \
					echo "⚠️  nvidia-smi found but could not detect CUDA version — falling back to CPU."; \
				fi; \
			elif [ "$$(uname)" = "Darwin" ] && [ "$$(uname -m)" = "arm64" ]; then \
				echo "🍎 Detected Apple Silicon — MPS acceleration will be used automatically."; \
			else \
				echo "💻 No GPU detected — using CPU-only PyTorch."; \
			fi; \
			;; \
		*) \
			echo "❌ Invalid GPU=$(GPU). Use cpu | auto | cuXXX (e.g. cu124)." >&2; \
			exit 2; \
			;; \
	esac
endef

# Post-sync torch wheel swap. After `uv sync`, if a CUDA index was resolved
# but the installed torch is still the CPU build, reinstall torch + vision +
# audio from the CUDA index. Idempotent: skips if torch is already CUDA.
define _maybe_install_cuda_torch
	@$(_resolve_gpu_index); \
	if [ -z "$$EXTRA_INDEX" ]; then \
		exit 0; \
	fi; \
	CURRENT_CUDA=$$(uv run --no-sync python -c "import torch; print(torch.version.cuda or '')" 2>/dev/null || echo ""); \
	if [ -n "$$CURRENT_CUDA" ]; then \
		echo "✅ torch already installed with CUDA $$CURRENT_CUDA — no swap needed."; \
		exit 0; \
	fi; \
	echo "🔁 Reinstalling torch torchvision torchaudio from $$EXTRA_INDEX..."; \
	uv pip install --reinstall torch torchvision torchaudio --index-url "$$EXTRA_INDEX"; \
	echo "✅ torch swapped to $$CUDA_TAG build."
endef

# ---------------------------------------------------------------------------
# Environment setup / install
# ---------------------------------------------------------------------------

setup: ## Set up dev environment (sync deps + Playwright + pre-commit + auto-swap CUDA torch + prefetch HF models). Override with GPU=cpu|cuXXX or NO_PREFETCH=1
	@echo "📦 Installing dependencies..."
	uv sync --group all-dev
	@echo "🌐 Installing Playwright Chromium browser and system dependencies..."
	uv run playwright install --with-deps chromium
	@echo "🪝 Setting up pre-commit hooks..."
	uv run pre-commit install
	$(_maybe_install_cuda_torch)
	@$(MAKE) --no-print-directory prefetch-models
	@echo "✅ Setup complete!"

install: ## Install pd-ocr-labeler as a uv tool + prefetch HF models (override with GPU=cpu|cuXXX or NO_PREFETCH=1)
	@$(_resolve_gpu_index); \
	echo "📦 Installing pd-ocr-labeler from local source..."; \
	if [ -n "$$EXTRA_INDEX" ]; then \
		uv tool install --reinstall . --extra-index-url "$$EXTRA_INDEX"; \
	else \
		uv tool install --reinstall .; \
	fi; \
	echo "✅ pd-ocr-labeler installed. Run: pd-ocr-labeler-ui ."
	@if [ -z "$$NO_PREFETCH" ]; then \
		echo "📥 Prefetching HF models..."; \
		pd-ocr-labeler-prefetch || echo "⚠️  Prefetch failed — models will download on first use."; \
	else \
		echo "ℹ️  NO_PREFETCH set — skipping HF model prefetch."; \
	fi

prefetch-models: ## Pre-warm HF cache for default OCR + layout models (skippable with NO_PREFETCH=1)
	@uv run --no-sync python -m pd_ocr_labeler.prefetch || echo "⚠️  Prefetch failed — models will download on first use."

uninstall: ## Remove the installed pd-ocr-labeler uv tool
	@echo "🗑️  Uninstalling pd-ocr-labeler..."
	uv tool uninstall pd-ocr-labeler || true
	@echo "✅ pd-ocr-labeler uninstalled."

remove-venv: ## Remove the virtual environment
	@echo "🗑️  Removing existing virtual environment..."
	rm -rf .venv
	@echo "✅ Virtual environment removed!"

reset: ## Rebuild virtual environment (keeps UV cache)
	@$(MAKE) --no-print-directory clean
	@$(MAKE) --no-print-directory remove-venv
	@$(MAKE) --no-print-directory setup
	@echo "✅ Environment Reset!"

reset-full: ## Nuclear option: clear everything and redownload
	@echo "🔄 FULL RESET: Clearing all caches and virtual environment..."
	@$(MAKE) --no-print-directory clean
	@$(MAKE) --no-print-directory remove-venv
	@echo "🧹 Clearing UV cache..."
	uv cache clean
	@echo "⬇️ Dependencies should download fresh now."
	@$(MAKE) --no-print-directory setup
	@echo "💥 Full reset complete! Everything is fresh!"

reinstall: reset ## Alias for reset (backward compatibility)

upgrade-deps: ## Upgrade dependencies and sync local environment (auto-swaps CUDA torch; override with GPU=cpu|cuXXX)
	@echo "⬆️ Upgrading dependency lockfile..."
	uv lock --upgrade
	@echo "📦 Syncing upgraded dependencies..."
	uv sync --group all-dev
	$(_maybe_install_cuda_torch)
	@echo "✅ Dependencies upgraded and environment synced!"

upgrade-pd-book-tools: ## Upgrade pd-book-tools pin to latest GitHub tag
	@echo "🔍 Fetching latest pd-book-tools tag..."
	$(eval LATEST_TAG := $(shell curl -sSf "https://api.github.com/repos/ConcaveTrillion/pd-book-tools/tags" | grep '"name"' | head -1 | sed 's/.*"name": "\(.*\)".*/\1/'))
	@if [ -z "$(LATEST_TAG)" ]; then echo "❌ Could not fetch latest tag." && exit 1; fi
	@echo "📌 Pinning to $(LATEST_TAG)..."
	@sed -i 's|pd-book-tools = { git = "https://github.com/ConcaveTrillion/pd-book-tools.git", tag = ".*" }|pd-book-tools = { git = "https://github.com/ConcaveTrillion/pd-book-tools.git", tag = "$(LATEST_TAG)" }|' pyproject.toml
	@echo "📦 Syncing..."
	uv sync --group all-dev
	@echo "✅ pd-book-tools upgraded to $(LATEST_TAG)!"

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test: ## Run tests with parallelization
	@echo "🧪 Running tests (parallelized)..."
	uv run pytest -n auto -v -ra

test-verbose: ## Run tests with verbose output and parallelization
	@echo "🧪 Running tests (verbose mode, parallelized)..."
	uv run pytest -n auto -v -ra

test-single: ## Run one pytest node id (usage: make test-single TEST='tests/...::test_name')
	@if [ -z "$(TEST)" ]; then \
		echo "❌ Missing TEST parameter."; \
		echo "   Example: make test-single TEST='tests/integration/test_url_routing.py::TestProjectRouting::test_project_route_nonexistent_shows_warning'"; \
		exit 1; \
	fi
	@echo "🧪 Running single test (parallelized): $(TEST)"
	uv run pytest -n auto "$(TEST)"

test-k: ## Run tests by pytest -k expression (usage: make test-k K='pattern')
	@if [ -z "$(K)" ]; then \
		echo "❌ Missing K parameter."; \
		echo "   Example: make test-k K='test_project_route_nonexistent_shows_warning'"; \
		exit 1; \
	fi
	@echo "🧪 Running tests with -k (parallelized): $(K)"
	uv run pytest -n auto -k "$(K)"

test-browser: ## Run browser-based regression tests (Playwright)
	@echo "🌐 Running browser tests (parallelized)..."
	uv run pytest -m browser -n auto -v -ra

coverage: ## Run tests with coverage report (parallelized)
	@echo "🧪 Running tests with coverage (parallelized)..."
	uv run pytest --cov=pd_ocr_labeler --cov-report=html -n auto -v -ra
	@echo "📊 Coverage report generated in htmlcov/index.html"

# ---------------------------------------------------------------------------
# Lint / format
# ---------------------------------------------------------------------------

lint: ## Run linting checks (Python + Markdown)
	@echo "🔍 Running linting checks..."
	@$(MAKE) --no-print-directory py-lint
	@$(MAKE) --no-print-directory md-lint

py-lint: ## Run Python linting checks
	@echo "🐍 Running Python linting checks..."
	uv run pre-commit run ruff-check --all-files

md-lint: ## Run Markdown linting checks
	@echo "📝 Running Markdown linting checks..."
	uv run pre-commit run markdownlint-cli2 --all-files

lint-fix: ## Auto-fix lint issues (Python + Markdown where supported)
	@echo "🛠️  Auto-fixing lint issues..."
	@$(MAKE) --no-print-directory py-lint-fix
	@$(MAKE) --no-print-directory md-lint-fix

py-lint-fix: ## Auto-fix Python lint issues
	@echo "🐍 Auto-fixing Python lint issues..."
	uv run pre-commit run ruff-format --all-files
	uv run pre-commit run ruff-check --all-files

md-lint-fix: ## Auto-fix Markdown lint issues
	@echo "📝 Auto-fixing Markdown lint issues..."
	uv run pre-commit run --hook-stage manual markdownlint-cli2-fix --all-files

format: ## Format code (ruff format, then lint)
	@echo "✨ Formatting code..."
	uv run ruff format
	@$(MAKE) --no-print-directory lint

pre-commit-check: ## Run pre-commit on all files
	@echo "🪝 Running pre-commit on all files..."
	uv run pre-commit run --all-files

# ---------------------------------------------------------------------------
# CI / build
# ---------------------------------------------------------------------------

ci: ## Run complete CI pipeline (setup [idempotent], pre-commit, test, build)
	@echo "🚀 Running complete CI pipeline..."
	@$(MAKE) --no-print-directory setup
	@$(MAKE) --no-print-directory pre-commit-check
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory build
	@echo "✅ CI pipeline complete!"

build: ## Build distribution packages (wheel and sdist)
	@echo "📦 Building distribution packages..."
	uv build
	@echo "✅ Build complete! Check dist/ directory for packages."

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

run: ## Run the OCR labeler UI with current directory as project
	@echo "🚀 Starting OCR Labeler UI..."
	uv run pd-ocr-labeler-ui .

run-verbose: ## Run the OCR labeler UI with verbose logging
	@echo "🚀 Starting OCR Labeler UI (verbose mode)..."
	uv run pd-ocr-labeler-ui . -vv

run-page-timing: ## Run the OCR labeler UI with isolated page timing logs
	@echo "🚀 Starting OCR Labeler UI (page timing mode)..."
	uv run pd-ocr-labeler-ui . --page-timing

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Clean up cache, temporary files, and logs (keeps venv and UV cache)
	@echo "🧹 Cleaning Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "🧹 Cleaning coverage files..."
	rm -rf htmlcov/ 2>/dev/null || true
	rm -f coverage.xml 2>/dev/null || true
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ 2>/dev/null || true
	rm -rf build/ 2>/dev/null || true
	@$(MAKE) --no-print-directory clean-logs
	@$(MAKE) --no-print-directory clean-cache
	@echo "✅ Cache cleanup complete!"

clean-logs: ## Remove session logs from OS-aware and legacy local paths
	@echo "🧹 Cleaning session logs..."
	uv run python -m pd_ocr_labeler.local_state_cleanup --logs
	@echo "✅ Log cleanup complete!"

clean-cache: ## Remove pre-rendered image cache from OS-aware and legacy local paths
	@echo "🧹 Clearing pre-rendered image cache..."
	uv run python -m pd_ocr_labeler.local_state_cleanup --cache
	@echo "✅ Image cache cleared! Pages will re-render on next load."

clean-image-cache: clean-cache ## Backward-compatible alias for clean-cache

# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------

release-patch: ## Bump patch version and create a git tag (e.g. 0.1.0 -> 0.1.1)
	uv version --bump patch
	@$(MAKE) --no-print-directory _do-release

release-minor: ## Bump minor version and create a git tag (e.g. 0.1.0 -> 0.2.0)
	uv version --bump minor
	@$(MAKE) --no-print-directory _do-release

release-major: ## Bump major version and create a git tag (e.g. 0.1.0 -> 1.0.0)
	uv version --bump major
	@$(MAKE) --no-print-directory _do-release

_do-release:
	@VERSION=$$(uv version --short); \
	git add pyproject.toml uv.lock; \
	git commit -m "chore: release v$$VERSION"; \
	git tag "v$$VERSION"; \
	echo "🏷️  Tagged v$$VERSION - push with: git push && git push --tags"
