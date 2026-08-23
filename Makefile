.PHONY: test api web dev

VENV := .venv/bin

test:
	$(VENV)/pytest backend/tests -q

api:
	$(VENV)/uvicorn app.main:app --reload --app-dir backend --port 8000

web:
	npm --prefix web run dev
