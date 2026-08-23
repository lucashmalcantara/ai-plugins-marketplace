PYTHON ?= python3

.PHONY: help validate sync check new

help:
	@echo "make validate      Validate the marketplace and every plugin"
	@echo "make sync          Regenerate both marketplace catalogs"
	@echo "make check         Fail if generated files are stale, then validate (used by CI)"
	@echo "make new NAME=x    Scaffold plugins/x from the template"

validate:
	$(PYTHON) scripts/validate.py

sync:
	$(PYTHON) scripts/sync_marketplaces.py

check:
	$(PYTHON) scripts/sync_marketplaces.py --check
	$(PYTHON) scripts/validate.py

new:
	@test -n "$(NAME)" || (echo "usage: make new NAME=my-plugin"; exit 1)
	$(PYTHON) scripts/new_plugin.py $(NAME)
