.PHONY: setup test lint typecheck check logs triage serve alert monitor triages eval judge-labels calibrate-judge tickets ui

PORT ?= 8000
ARM ?= rag
REPETITIONS ?= 1
EXPERIMENTS ?=
SECONDS_PER_CHECK ?= 1
ALERT_FILE ?= data/alerts/checkout_error_rate.json
ALERT ?= ALR-8812: checkout-service 5xx error rate 18% (threshold 5%) since 2026-11-17T02:09:00Z

setup:
	uv sync
	test -f .env || cp sample.env .env

test:
	uv run pytest -n auto --random-order --random-order-bucket=global

lint:
	uv run ruff check --fix && uv run ruff format

typecheck:
	uv run ty check

check: lint typecheck test

logs:
	uv run generate-mock-logs

triage:
	uv run incident-triage "$(ALERT)"

serve:
	uv run uvicorn triage_api.main:app --port $(PORT)

alert:
	curl -s -X POST localhost:$(PORT)/alerts -H 'Content-Type: application/json' -d @$(ALERT_FILE)

monitor:
	uv run error-monitor --api-url http://localhost:$(PORT) --seconds-per-check $(SECONDS_PER_CHECK)

triages:
	curl -s localhost:$(PORT)/triages | uv run python -m json.tool

eval:
	uv run run-evals --arm $(ARM) --repetitions $(REPETITIONS)

judge-labels:
	uv run calibrate-judge export --experiments $(EXPERIMENTS)

calibrate-judge:
	uv run calibrate-judge score

tickets:
	uv run python -m json.tool data/jira/tickets.json

ui:
	uv run --group ui python -m triage_ui.app
