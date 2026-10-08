.PHONY: help api web test health prod-up prod-down

help:
	@echo "api      - run FastAPI on :8000"
	@echo "web      - run Next.js on :3000"
	@echo "test     - pytest"
	@echo "health   - curl /v1/health"
	@echo "prod-up  - Contabo-style stack (docker-compose.prod.yml + .env.prod)"
	@echo "prod-down - stop production compose stack"

api:
	uvicorn apps.api.main:app --reload --port 8000

web:
	cd apps/web && npm install && npm run dev

test:
	pytest -q

health:
	curl -s http://localhost:8000/v1/health | python -m json.tool

prod-up:
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml --env-file .env.prod down
