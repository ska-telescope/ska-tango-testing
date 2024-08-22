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
# Variables to run just a subset of the tests


PYTHON_TEST_NAME ?=## Name of your test target (it will be passed to pytest through -k) 
PYTHON_VARS_AFTER_PYTEST += -k '$(PYTHON_TEST_NAME)'

# Example: make python-test
#	PYTHON_TEST_NAME="TangoEventTracer or TangoEventLogger or TestCustomPredicates or TestCustomAssertions or TestTypedEvents or TestChainedAssertionsTimeout"
# will run only the tests that match the given names

PYTHON_TEST_MARK ?=## Mark of your test target (it will be passed to pytest through -m)
ifneq ($(PYTHON_TEST_MARK),)
	PYTHON_VARS_AFTER_PYTEST += -m '$(PYTHON_TEST_MARK)'
endif

# Example: make python-test PYTHON_TEST_MARK="integration_tracer"
# will run only the tests related to ``integration`` submodule
# (e.g., tango event tracer, tango event logger, assertpy assertions, etc.)
