.PHONY: fmt
lint:
	black --check .
	isort --check-only .
	flake8 .

.PHONY: fmt
fmt:
	black .
	isort .

.PHONY: test
test:
	pytest .
