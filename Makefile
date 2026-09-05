# ElevatorOS — Project Makefile
#
# Usage:
#   make verify    Run all project checks (tests, types, packaging)
#
# This Makefile works from the repository root. The Python project
# lives under backend/, and all commands cd into that directory first.

BACKEND_DIR := backend
PYTHON := .venv/bin/python

.PHONY: verify test typecheck packaging

verify: test typecheck packaging
	@echo ""
	@echo "✅  All checks passed."

test:
	@echo "── pytest ─────────────────────────────────────────────"
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v

typecheck:
	@echo ""
	@echo "── mypy ───────────────────────────────────────────────"
	cd $(BACKEND_DIR) && $(PYTHON) -m mypy app tests

packaging:
	@echo ""
	@echo "── packaging ──────────────────────────────────────────"
	cd $(BACKEND_DIR) && $(PYTHON) -m pip install -e ".[dev]" --quiet
	@echo "Editable install: OK"
