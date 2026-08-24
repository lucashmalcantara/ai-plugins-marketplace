PYTHON ?= python3

.PHONY: help validate sync check test new

help:
	@echo "make validate      Validate the marketplace and every plugin"
	@echo "make sync          Regenerate both marketplace catalogs"
	@echo "make test          Run the plugin script tests"
	@echo "make check         Fail if generated files are stale, then validate and test (used by CI)"
	@echo "make new NAME=x    Scaffold plugins/x from the template"

validate:
	$(PYTHON) scripts/validate.py

sync:
	$(PYTHON) scripts/sync_marketplaces.py

check:
	$(PYTHON) scripts/sync_marketplaces.py --check
	$(PYTHON) scripts/validate.py
	$(MAKE) test

test:
	@found=0; \
	for dir in plugins/*/scripts; do \
		[ -d "$$dir" ] || continue; \
		ls "$$dir"/test_*.py >/dev/null 2>&1 || continue; \
		found=1; echo "==> $$dir"; \
		$(PYTHON) -m unittest discover -s "$$dir" -p 'test_*.py' || exit 1; \
	done; \
	[ "$$found" = 1 ] || echo "no plugin script tests found"

new:
	@test -n "$(NAME)" || (echo "usage: make new NAME=my-plugin"; exit 1)
	$(PYTHON) scripts/new_plugin.py $(NAME)
