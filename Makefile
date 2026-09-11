.PHONY: help test test-pdf example gallery doctor

PYTHON ?= python3
POEM := PYTHONPATH=src $(PYTHON) -m poemtex.cli

help:
	@echo "PoemTeX development commands"
	@echo "  make test      Fast parser, renderer, CLI, and gallery tests"
	@echo "  make test-pdf  Tests every theme with real LuaLaTeX"
	@echo "  make example   Builds the example collection"
	@echo "  make gallery   Builds all visual theme previews"
	@echo "  make doctor    Checks local TeX and font dependencies"

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

test-pdf:
	PYTHONPATH=src POEMTEX_PDF_TESTS=1 $(PYTHON) -m unittest discover -s tests -v

example:
	$(POEM) build examples/swiatlo-i-cisza/book.poem

gallery:
	$(POEM) gallery examples/swiatlo-i-cisza/book.poem

doctor:
	$(POEM) doctor
