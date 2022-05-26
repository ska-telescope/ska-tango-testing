include .make/base.mk
include .make/python.mk

DOCS_SPHINXOPTS=-n -W --keep-going

python-post-format:
	docformatter -r -i --pre-summary-newline src/ tests/

python-post-lint:
	mypy --config-file mypy.ini src/ tests/

.PHONY: python-post-format python-post-lint
