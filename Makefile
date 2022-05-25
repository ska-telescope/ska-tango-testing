include .make/base.mk
include .make/python.mk

PYTHON_RUNNER=poetry run

DOCS_SPHINXOPTS=-n -W --keep-going

python-post-format:
	$(PYTHON_RUNNER) docformatter -r -i --pre-summary-newline src/ tests/

python-post-lint:
	$(PYTHON_RUNNER) mypy --config-file mypy.ini src/ tests/

.PHONY: python-post-format python-post-lint
