include .make/base.mk
include .make/python.mk

PYTHON_RUNNER=poetry run

DOCS_SPHINXOPTS=-n -W --keep-going

python-post-format:
	$(PYTHON_RUNNER) docformatter -r -i --pre-summary-newline src/ tests/

python-post-lint:
	$(PYTHON_RUNNER) mypy --config-file mypy.ini src/ tests/

python-do-build:
	poetry build

python-do-publish:
	poetry config repositories.skao $(PYTHON_PUBLISH_URL)
	poetry publish --repository skao --username $(PYTHON_PUBLISH_USERNAME) --password $(PYTHON_PUBLISH_PASSWORD)

.PHONY: python-post-format python-post-lint python-do-build python-do-publish
