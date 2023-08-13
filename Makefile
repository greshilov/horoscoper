.PHONY: init
init:
	poetry install --with dev

.PHONY: fmt
lint:
	poetry run black --check .
	poetry run isort --check-only .
	poetry run flake8 .

.PHONY: fmt
fmt:
	poetry run black .
	poetry run isort .

redis:
	docker compose -p horoscoper-dev -f docker-compose.dev.yml up -d

.PHONY: test
test:
	poetry run pytest -v .

.PHONY: dev
dev-api: redis
	REDIS_URL=redis://localhost:36379/0 poetry run uvicorn horoscoper.api.main:app --reload --log-level debug

.PHONY: worker
dev-worker: redis
	REDIS_URL=redis://localhost:36379/0 poetry run python -m horoscoper.tasks.infer

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build

.PHONY: clean
clean:
	docker compose -p horoscoper-dev -f docker-compose.dev.yml down -v
