.PHONY: fmt
lint:
	black --check .
	isort --check-only .
	flake8 .

.PHONY: fmt
fmt:
	black .
	isort .

redis:
	docker compose -p horoscoper-dev -f docker-compose.dev.yml up -d

.PHONY: test
test: redis
	REDIS_URL=redis://localhost:36379/0 pytest .

.PHONY: dev
dev-api: redis
	REDIS_URL=redis://localhost:36379/0 uvicorn horoscoper.api.main:app --reload --log-level debug

.PHONY: worker
dev-worker: redis
	REDIS_URL=redis://localhost:36379/0 python -m horoscoper.tasks.infer

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build

.PHONY: clean
clean:
	docker compose -p horoscoper-dev -f docker-compose.dev.yml down -v
