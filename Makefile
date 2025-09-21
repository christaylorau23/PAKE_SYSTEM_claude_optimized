# PAKE System Makefile        print(f'  {repo}: {stat}')
    await dal.cleanup()

asyncio.run(show_stats())
"

# Deployment
build:  ## Build application for deployment
	@echo "Building PAKE System for deployment..."
	python setup.py bdist_wheel
	@echo "Build complete! Artifacts in dist/"

docker-build:  ## Build Docker image
	docker build -t pake-system:latest .
	@echo "Docker image built: pake-system:latest"

docker-run:  ## Run Docker container
	docker run -p 8000:8000 pake-system:latest

# Data Management
backup:  ## Backup system data
	@echo "Creating system backup..."
	python scripts/backup_system.py
	@echo "Backup complete!"

restore:  ## Restore system from backup
	@echo "Restoring system from backup..."
	@read -p "Enter backup file path: " backup_file; python scripts/restore_system.py "$$backup_file"

# Cleanup
clean:  ## Clean up temporary files and caches
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	@echo "Cleanup complete!"

clean-all: clean  ## Clean everything including dependencies
	rm -rf venv/
	rm -rf .venv/
	@echo "Full cleanup complete!"

# Git Helpers
git-status:  ## Show enhanced git status
	@echo "Git Status Overview:"
	@echo "==================="
	git status --short
	@echo ""
	@echo "Recent Commits:"
	@echo "==============="
	git log --oneline -5

git-branches:  ## Show local and remote branches
	@echo "Local Branches:"
	@echo "==============="
	git branch -v
	@echo ""
	@echo "Remote Branches:"
	@echo "================"
	git branch -r

# Performance
benchmark:  ## Run system benchmarks
	@echo "Running system benchmarks..."
	python scripts/benchmark_system.py
	@echo "Benchmark complete! Results in benchmarks/"

profile:  ## Profile application performance
	@echo "Profiling application performance..."
	python -m cProfile -o profile.stats scripts/profile_app.py
	@echo "Profile complete! Results in profile.stats"

# Utilities
generate-config:  ## Generate default configuration files
	@echo "Generating default configuration..."
	python scripts/generate_config.py
	@echo "Configuration files generated!"

validate-config:  ## Validate configuration files
	@echo "Validating configuration files..."
	python scripts/validate_config.py
	@echo "Configuration validation complete!"

check-deps:  ## Check for dependency updates
	@echo "Checking for dependency updates..."
	pip list --outdated
	@echo "Dependency check complete!"

# Development Workflow Helpers
feature-start:  ## Start new feature branch (usage: make feature-start name=feature-name)
	@if [ -z "$(name)" ]; then echo "Usage: make feature-start name=feature-name"; exit 1; fi
	git checkout -b feature/$(name)
	@echo "Created and switched to feature branch: feature/$(name)"

feature-finish:  ## Finish feature branch and merge to main
	@branch=$$(git branch --show-current); \
	if [[ $$branch != feature/* ]]; then echo "Not on a feature branch!"; exit 1; fi; \
	echo "Finishing feature branch: $$branch"; \
	git checkout main; \
	git merge $$branch; \
	git branch -d $$branch; \
	echo "Feature branch $$branch merged and deleted"

release-prep:  ## Prepare for release (run tests, update version, etc.)
	@echo "Preparing for release..."
	$(MAKE) test-coverage
	$(MAKE) lint
	$(MAKE) security-scan
	@echo "Release preparation complete!"

# CI/CD Simulation
ci-local:  ## Simulate CI pipeline locally
	@echo "Running local CI pipeline..."
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) security-scan
	$(MAKE) test-coverage
	@echo "Local CI pipeline complete!"

# Quick Start
quickstart:  ## Quick setup for new developers
	@echo "PAKE System Quick Start"
	@echo "======================="
	@echo "1. Setting up development environment..."
	$(MAKE) setup-dev
	@echo "2. Running tests to verify setup..."
	$(MAKE) test
	@echo "3. Checking system health..."
	$(MAKE) health-check
	@echo ""
	@echo "✅ Quick start complete!"
	@echo "Next steps:"
	@echo "  - Read CONTRIBUTING.md for development guidelines"
	@echo "  - Check ROADMAP.md for upcoming features"
	@echo "  - Run 'make vector-setup' to enable vector memory features"
	@echo "  - Run 'make run-dev' to start the development server"

# Show current project status
status:  ## Show comprehensive project status
	@echo "PAKE System Status"
	@echo "=================="
	@echo "Git Status:"
	$(MAKE) git-status
	@echo ""
	@echo "System Health:"
	$(MAKE) health-check
	@echo ""
	@echo "Recent Test Results:"
	@if [ -f .pytest_cache/v/cache/lastfailed ]; then echo "Some tests failed in last run"; else echo "All tests passed in last run"; fi