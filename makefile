.PHONY: help api web test health

help:
	@echo "api    - run FastAPI on :8000"
	@echo "web    - run empty Next.js scaffold on :3000"
	@echo "test   - pytest"
	@echo "health - curl /v1/health"

api:
	uvicorn apps.api.main:app --reload --port 8000

web:
	cd apps/web && npm install && npm run dev

test:
	pytest -q

health:
	curl -s http://localhost:8000/v1/health | python -m json.tool
