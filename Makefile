.PHONY: test api web dev

VENV := .venv/bin

test:
	$(VENV)/pytest backend/tests -q

api:
	$(VENV)/uvicorn app.main:app --reload --app-dir backend --port 8000

web:
	npm --prefix web run dev

dev:
	@echo "Run make api and make web in two terminals (or npm run dev after the API is up)."
