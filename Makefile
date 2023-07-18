include .make/base.mk
include .make/python.mk

DOCS_SPHINXOPTS=-W --keep-going

python-post-lint:
	mypy --config-file mypy.ini src/ tests/

docs-pre-build:
	poetry config virtualenvs.create false
	poetry install --no-root --only docs

.PHONY: python-post-lint docs-pre-build
