include .make/base.mk
include .make/python.mk

DOCS_SPHINXOPTS=-W --keep-going

python-post-lint:
	mypy --config-file mypy.ini src/ tests/

docs-pre-build:
	poetry config virtualenvs.create false
	poetry install --no-root --only docs

.PHONY: python-post-lint docs-pre-build

# #############################################
# Variable to run just a subset of the tests
# (it will be used when calling pytest, 
# with the `-k` option)

PYTHON_TEST_NAME ?=## Name of your test target (it will be passed to pytest through -k) 
PYTHON_VARS_AFTER_PYTEST := $(PYTHON_VARS_AFTER_PYTEST) -k '$(PYTHON_TEST_NAME)'

# Example: make python-test
#	PYTHON_TEST_NAME="TangoEventTracer or TangoEventLogger or TestCustomPredicates or TestCustomAssertions"
# will run only the tests that match the given names