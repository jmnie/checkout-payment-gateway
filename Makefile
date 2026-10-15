.PHONY: test python-test java-test e2e up down

test: python-test java-test

python-test:
	cd python && uv sync --locked && uv run ruff check . && uv run pytest --cov=payment_gateway_api

java-test:
	cd java && ./gradlew test bootJar --no-daemon

e2e: test
	npm ci --ignore-scripts
	uv run --project python python scripts/e2e.py

up:
	docker compose up --build --wait

down:
	docker compose down
