.PHONY: clean test build help

help:
	@echo "Yamlr Development Makefile"
	@echo "  make clean    - Purge transient files and caches"
	@echo "  make test     - Run the full test suite"
	@echo "  make build    - Build the native binary (Nuitka)"

clean:
	python scripts/clean.py

test:
	pytest tests/

build:
	python scripts/build_nuitka.py
