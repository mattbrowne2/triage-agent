# AGENTS.md

## Purpose

An incident triage agent built on LangChain `create_agent`. Given a production alert, it investigates Datadog-style logs with tools and writes a triage summary. Evaluation runs on LangSmith.

## Layout

- `src/incident_triage/settings.py`: `Settings` and `get_settings()`. Modules declare `_settings = get_settings()`.
- `src/incident_triage/models/`: Pydantic models only (Datadog logs, log search, tool names, the `Alert` contract, and the `TriageReport` structured output).
- `src/incident_triage/log_store/`: the log repository, filters and domain errors.
- `src/incident_triage/jira/`: the dummy Jira store and its errors (one ticket per alert, PII rejected). `src/incident_triage/pii.py` holds the shared email detection.
- `src/incident_triage/incident_store/`: the past-incident vector index (RAG), the document text each ticket is embedded as, and the embeddings factory.
- `src/incident_triage/tools/`: LangChain tools built by factories; descriptions live in `tools/descriptions/*.md`.
- `src/incident_triage/agent/`: chat model factory, agent factory, and the system prompt in `agent/prompts/`.
- `src/incident_triage/runner.py`: streams agent messages.
- `src/incident_triage/wiring.py`: `AgentToolkit` builds the shared resources once; `build_agent_factory` gives a per-alert agent (the ticket tool is tied to the alert's key). Shared by the CLI and the API.
- `src/incident_triage/main.py`: CLI entrypoint.
- `src/monitor/`: the error-rate monitor: sliding `window.py`, the per-service state machine in `error_rate_monitor.py`, `replay.py` over an archive, and `client.py`, which posts `Alert`s to the API.
- `src/triage_api/`: FastAPI service that receives `Alert`s and runs triages in the background. Routes in `routes/`, in-memory `TriageStore`, `worker.run_triage`.
- `src/evals/`: the eval harness: case models, LangSmith dataset upload, the per-case target, deterministic evaluators, the slice summary and the `run-evals` CLI. Cases live in `data/evals/triage_cases.json`; summaries in `eval_results/`. `src/evals/judge/` holds the LLM judge (rubric in `prompts/judge.md`) and the `calibrate-judge` CLI.
- `src/triage_ui/`: the Gradio demo page (`make ui`). Presentation only: exempt from TDD and `ty` by the owner's choice; keep logic out of it.
- `src/mock_logs/`: a deterministic generator for mock Datadog log archives, one module per scenario in `scenarios/`.
- `data/datadog_logs/`: generated archives. Regenerate with `make logs`; never edit them by hand.
- `data/incidents/`: hand-written past incident tickets for retrieval.

## Non-negotiable engineering rules

### TDD is mandatory

1. RED: write a failing test.
2. GREEN: write the minimal implementation that passes it.
3. REFACTOR: improve the structure.

Every production change needs a test.

### Testing style

- Tests live in `tests/unit/` and mirror `src/`.
- Read `tests/unit/conftest.py` before writing tests, and reuse its fixtures.
- Use pytest only, with function tests and no classes. Follow Arrange / Act / Assert without labelling the sections.
- Name tests after the behaviour they check.
- Use fixtures in `conftest.py`, not helper functions.
- Prefer real objects over mocks. Mock only external systems; LLMs are faked with `scripted_chat_model_factory` and embeddings with `fake_embeddings`. Tests run with `INCIDENT_SEARCH_ENABLED=false` so nothing calls the embeddings API.
- Assert full objects. Don't assert counts or patterns when the exact values are known.
- Run with `make test`.

## Coding standards

- Python 3.12, with full type annotations and modern syntax (`X | Y`, `match`, `StrEnum`).
- Use Pydantic models for all structured data. No bare `dict` or `list`.
- Absolute imports only, with no imports inside functions.
- Keep modules small and split by responsibility. Models go in `models/`.
- No comments and no docstrings. Express intent through names and types.
- Run `make lint` and `make typecheck` before committing.

## Errors: handle them, don't avoid them

- No defensive code: no `.get()` or `getattr(..., default)`, and no guarding against impossible states.
- When a failure is expected (bad tool input, unknown service, step limit reached), raise a domain error and handle it explicitly where it can be acted on. For example, tools convert `LogSearchError` into a `ToolException` so the agent sees the message and can correct itself.
- Put cross-field validation in the domain layer, not in tool argument schemas: LangGraph sends the model an empty message for model-level Pydantic validator errors.

## Agent design

- Keep the agentic loop lightweight: `create_agent` plus tools and a system prompt. Don't hard-code tool sequences or orchestrate reasoning in code.
- The system prompt holds behaviour and constraints only, not workflows or tool instructions.
- Each tool description covers what the tool does, when to use it, when not to use it, its inputs and outputs, and examples.
- Model and provider come from settings (`LLM_PROVIDER`, `LLM_MODEL`). Never hard-code them.

## Secrets and config

- Never hard-code secrets. Document every variable in `sample.env`. `.env` is gitignored.
