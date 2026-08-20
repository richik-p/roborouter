.PHONY: dev api web worker install generate test lint typecheck docs-check check db-up db-down seed

install:
	uv sync --all-packages --dev
	npm install

dev:
	docker compose -f infra/compose.yml up -d postgres minio minio-init

api:
	uv run alembic upgrade head
	uv run uvicorn roborouter_api.main:app --app-dir services/api/src --reload --port 8000

web:
	npm run dev

worker:
	uv run roborouter-worker

generate:
	uv run python scripts/generate_contracts.py
	uv run python scripts/generate_openapi.py
	npm exec -- openapi-typescript packages/contracts/generated/openapi.json -o apps/web/lib/api.generated.ts

test:
	uv run pytest

lint:
	uv run ruff check packages services scripts
	npm run lint

typecheck:
	npm run typecheck

docs-check:
	uv run python scripts/check_markdown_links.py

check: generate test lint typecheck docs-check
	npm run build

db-up:
	docker compose -f infra/compose.yml up -d

db-down:
	docker compose -f infra/compose.yml down

seed:
	uv run roborouter-seed
