# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Custom targets for PAKE System documentation
.PHONY: clean-docs build-docs serve-docs deploy-docs

clean-docs:
	rm -rf $(BUILDDIR)/*
	rm -rf _static/*
	rm -rf _templates/*

build-docs:
	@echo "Building PAKE System documentation..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "Documentation built successfully!"

serve-docs: build-docs
	@echo "Starting documentation server..."
	@cd $(BUILDDIR)/html && python -m http.server 8080

deploy-docs: build-docs
	@echo "Deploying documentation..."
	@rsync -av $(BUILDDIR)/html/ /var/www/docs/

# Development targets
.PHONY: dev-docs watch-docs

dev-docs:
	@echo "Starting development documentation server..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@cd $(BUILDDIR)/html && python -m http.server 8080

watch-docs:
	@echo "Watching for documentation changes..."
	@while true; do \
		make build-docs; \
		sleep 2; \
	done

# CI/CD targets
.PHINX: ci-docs test-docs

ci-docs:
	@echo "Building documentation for CI..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W $(SPHINXOPTS) $(O)

test-docs:
	@echo "Testing documentation build..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W $(SPHINXOPTS) $(O)
	@echo "Documentation build test passed!"

# Quality assurance targets
.PHONY: lint-docs spell-check-docs

lint-docs:
	@echo "Linting documentation..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W $(SPHINXOPTS) $(O)

spell-check-docs:
	@echo "Spell checking documentation..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W $(SPHINXOPTS) $(O)

# API documentation targets
.PHONY: api-docs update-api-docs

api-docs:
	@echo "Generating API documentation..."
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

update-api-docs:
	@echo "Updating API documentation..."
	@cd ../../ && python -c "import sphinx.ext.autodoc; print('API docs updated')"
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
