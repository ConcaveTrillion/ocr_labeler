.PHONY: install setup reinstall reset-venv reset-full upgrade-deps test test-single test-k lint format pre-commit-check build clean clean-logs help

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and set up development environment
	@echo "📦 Installing dependencies..."
	uv sync --group all-dev
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

test: ## Run tests
	@echo "🧪 Running tests..."
	uv run pytest

test-verbose: ## Run tests with verbose output
	@echo "🧪 Running tests (verbose mode)..."
	uv run pytest -v

test-single: ## Run one pytest node id (usage: make test-single TEST='tests/...::test_name')
	@if [ -z "$(TEST)" ]; then \
		echo "❌ Missing TEST parameter."; \
		echo "   Example: make test-single TEST='tests/integration/test_url_routing.py::TestProjectRouting::test_project_route_nonexistent_shows_warning'"; \
		exit 1; \
	fi
	@echo "🧪 Running single test: $(TEST)"
	uv run pytest "$(TEST)"

test-k: ## Run tests by pytest -k expression (usage: make test-k K='pattern')
	@if [ -z "$(K)" ]; then \
		echo "❌ Missing K parameter."; \
		echo "   Example: make test-k K='test_project_route_nonexistent_shows_warning'"; \
		exit 1; \
	fi
	@echo "🧪 Running tests with -k: $(K)"
	uv run pytest -k "$(K)"

coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	uv run pytest --cov=ocr_labeler --cov-report=html
	@echo "📊 Coverage report generated in htmlcov/index.html"

lint: ## Run linting checks
	@echo "🔍 Running linting checks..."
	uv run ruff check --select I --fix
	uv run ruff check --fix

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

clean: ## Clean up cache and temporary files (keeps venv and UV cache)
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
	@echo "✅ Cache cleanup complete!"

clean-logs: ## Remove all session logs from logs/
	@echo "🧹 Cleaning session logs..."
	find logs -type f -name "*.log" -delete 2>/dev/null || true
	@echo "✅ Log cleanup complete!"
