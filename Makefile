include .make/base.mk
include .make/python.mk

DOCS_SPHINXOPTS=-W --keep-going

python-post-lint:
	mypy --config-file mypy.ini src/ tests/

docs-pre-build:
	poetry config virtualenvs.create false
	poetry install --no-root --only docs

.PHONY: python-post-lint docs-pre-build

# Variable to specify the test
# (it will be used when calling pytest, with the `-k` option)
TEST_TARGET ?= TangoEventTracer or TangoEventLogger or TestCustomPredicates

# Run a single test
python-test-focused: PYTHON_VARS_AFTER_PYTEST := --tb=long -k '$(TEST_TARGET)' $(PYTHON_VARS_AFTER_PYTEST)
python-test-focused: python-test