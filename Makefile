.PHONY: install setup reinstall reset-venv reset-full upgrade-deps test test-single test-k test-browser lint py-lint md-lint lint-fix py-lint-fix md-lint-fix format pre-commit-check build clean clean-logs clean-cache clean-image-cache help run run-verbose run-page-timing release-patch release-minor release-major _do-release

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and set up development environment
	@echo "📦 Installing dependencies..."
	uv sync --group all-dev
	@echo "🌐 Installing Playwright Chromium browser and system dependencies..."
	uv run playwright install --with-deps chromium
	@echo "🪝 Setting up pre-commit hooks..."
	uv run pre-commit install
	@echo "✅ Installation complete!"

setup: install ## Alias for install

reinstall: reset-venv ## Alias for reset-venv (backward compatibility)

remove-venv: ## Remove the virtual environment
	@echo "🗑️  Removing existing virtual environment..."
	rm -rf .venv
	@echo "✅ Virtual environment removed!"

reset: ## Rebuild virtual environment (keeps UV cache)
	@$(MAKE) --no-print-directory clean
	@$(MAKE) --no-print-directory remove-venv
	@$(MAKE) --no-print-directory install
	@echo "✅ Environment Reset!"

reset-full: ## Nuclear option: clear everything and redownload
	@echo "🔄 FULL RESET: Clearing all caches and virtual environment..."
	@$(MAKE) --no-print-directory clean
	@$(MAKE) --no-print-directory remove-venv
	@echo "🧹 Clearing UV cache..."
	uv cache clean
	@echo "⬇️ Dependencies should download fresh now."
	@$(MAKE) --no-print-directory install
	@echo "💥 Full reset complete! Everything is fresh!"

upgrade-deps: ## Upgrade dependencies and sync local environment
	@echo "⬆️ Upgrading dependency lockfile..."
	uv lock --upgrade
	@echo "📦 Syncing upgraded dependencies..."
	uv sync --group all-dev
	@echo "✅ Dependencies upgraded and environment synced!"

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
	uv run pytest --cov=ocr_labeler --cov-report=html -n auto -v -ra
	@echo "📊 Coverage report generated in htmlcov/index.html"

lint: ## Run linting checks
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

format: ## Format code
	@echo "✨ Formatting code..."
	uv run ruff format
	@$(MAKE) --no-print-directory lint

pre-commit-check: ## Run pre-commit on all files
	@echo "🪝 Running pre-commit on all files..."
	uv run pre-commit run --all-files

ci: ## Run complete CI pipeline (install [idempotent], pre-commit, test, build)
	@echo "🚀 Running complete CI pipeline..."
	@$(MAKE) --no-print-directory install
	@$(MAKE) --no-print-directory pre-commit-check
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory build
	@echo "✅ CI pipeline complete!"

build: ## Build distribution packages (wheel and sdist)
	@echo "📦 Building distribution packages..."
	uv build
	@echo "✅ Build complete! Check dist/ directory for packages."

run: ## Run the OCR labeler UI with current directory as project
	@echo "🚀 Starting OCR Labeler UI..."
	uv run ocr-labeler-ui .

run-verbose: ## Run the OCR labeler UI with verbose logging
	@echo "🚀 Starting OCR Labeler UI (verbose mode)..."
	uv run ocr-labeler-ui . -vv

run-page-timing: ## Run the OCR labeler UI with isolated page timing logs
	@echo "🚀 Starting OCR Labeler UI (page timing mode)..."
	uv run ocr-labeler-ui . --page-timing

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
	uv run python -m ocr_labeler.local_state_cleanup --logs
	@echo "✅ Log cleanup complete!"

clean-cache: ## Remove pre-rendered image cache from OS-aware and legacy local paths
	@echo "🧹 Clearing pre-rendered image cache..."
	uv run python -m ocr_labeler.local_state_cleanup --cache
	@echo "✅ Image cache cleared! Pages will re-render on next load."

clean-image-cache: clean-cache ## Backward-compatible alias for clean-cache

clean-lc-run-verbose:
	@$(MAKE) --no-print-directory clean-logs
	@$(MAKE) --no-print-directory clean-image-cache
	@$(MAKE) --no-print-directory run-verbose

clean-l-run-verbose:
	@$(MAKE) --no-print-directory clean-logs
	@$(MAKE) --no-print-directory run-verbose

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
