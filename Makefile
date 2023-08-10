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

.PHONY: dev
dev:
	uvicorn horoscoper.api.main:app --reload --log-level debug


.PHONY: worker
worker:
	rq worker
