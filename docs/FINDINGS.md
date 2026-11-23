# Findings

What broke, what changed as a result. Versions at the time: `langchain` 1.5.2, `langchain-core` 1.8.3, `langchain-anthropic` 1.7.11, `langgraph` 1.2.23.

## Framework Findings

**1. `ToolStrategy` doesn't work on `claude-sonnet-5-5`.** `create_agent` with `ToolStrategy` forces tool use (`tool_choice="any"`), and the API rejects forced tool use while thinking is on. On this model thinking is always on. `langchain-anthropic` can work around this, but only when `thinking` is set explicitly, so the first live call failed with a 400. All unit tests had passed, because the fake chat model accepts any `tool_choice`. *Fix:* Anthropic now uses `ProviderStrategy` (native structured output) and OpenAI keeps `ToolStrategy` (`agent/response_format.py`). With `ProviderStrategy`, a report that fails to parse isn't retried, so the runner handles that error explicitly. *Lesson:* fake models test logic, not provider contracts. A small opt-in live smoke test for each provider would have caught this.

**2. Model-level Pydantic validator errors reach the agent as an empty message.** A `model_validator` that checked `end > start` produced "Error invoking tool … with error: \n Please fix the error", with the reason blank. *Fix:* cross-field checks moved to the domain layer and are raised as `LogSearchError`, which the tool converts to `ToolException`. The rule is in `AGENTS.md`.

**3. Duplicate tool-call IDs crash the router** with `KeyError: 'model'`. This was a test artifact, since real providers generate unique IDs, but it matters if you replay or synthesise trajectories.

**4. A plain-text final answer ends the run with no report.** With tools bound, `create_agent` stops as soon as an AI message has no tool calls. It doesn't ask again.

**5. The unit tests were sending traces to LangSmith.** `get_settings()` loads `.env`, which turned tracing on for the whole test process. Nothing failed. *Fix:* `tests/unit/conftest.py` sets `LANGSMITH_TRACING="false"` before any import.

## Agent behaviour

**6. First live runs got the right answer but investigated narrowly.** Claude and GPT both found the payment-service v2.14.0 `currency_code` rejection, but neither looked at the inventory-service red herring: they filtered by service from the first call. Claude pulled 50 logs per search (about 25k characters), while GPT used limits of 8–15 and was more careful about claims it couldn't verify. Customer emails reached the model and the trace through the raw tool output.

**7. One incident produces two alerts, two triages and two tickets.** The monitor correctly fires for both checkout-service and web-frontend at 02:10, and both triages trace back to the same payment deploy. Options: group alerts in the API by time, use the service dependency graph to triage only the deepest alerting service, or give the agent a tool to find open incidents. With more time I would look into grouping errors by a correlation_id, which is typically something done at the logging level within the microservices.

## Retrieval and evals

**8. Similarity threshold.** With `text-embedding-3-small`, unrelated queries score at most 0.37, the right ticket scores 0.68–0.84, and tickets on the same topic with a different cause score 0.40–0.53, so `INCIDENT_MIN_SIMILARITY` is 0.5. A vague query ("checkout 500 errors") ranks the TLS look-alike INC-298 above the true match, which is why the tool description says to search with what the agent observed, not with the alert text. Retrieval alone can't reject INC-298; in practice the agent rejects it using the logs.

**9. "RAG improves root cause" didn't replicate.** The first eval had root-cause accuracy of 0.76 for the baseline against 0.90 for RAG, and the rerun had 0.95 against 0.86. Eight cases with three repetitions can't detect a difference that size. What does hold up: the look-alike was never cited, and confidence was better calibrated with RAG (judge 0.83 against 1.00).

**10. A pattern-summary tool and one prompt line fixed the red herring.** `summarize_log_patterns` turns 520 logs into 16 patterns, and the prompt now says to account for every other service showing warnings or errors around the incident. `ruled_out_expected` went from 0.39 to 1.00 in both arms, with no increase in tool calls. The same change added `create_jira_ticket`, and 47 of 48 ticket decisions were correct (`triage-baseline-3923228f`, `triage-rag-18ddaf9a`). The tool and the prompt line changed together, so their individual effects aren't separated.

**11. Open issues from the latest eval.**
- **Next steps:** `judge_next_steps_actionable` fell to 0.67 in the RAG arm. The agent suggests investigating the commit before rolling back. That rubric line is a judgment call, and my labels disagreed with it (finding 12).
- **Confidence on the false alarm:** the agent reports "high" confidence that there's no incident while admitting it can't see the relevant logs. The judge catches this; the deterministic checks don't.
- **A probably-wrong label:** `human-wrong-service` expects INC-287 to be cited, but with the pattern tool the agent rules out inventory directly. Labels need reviewing whenever the agent's capabilities change.

**12. Judge calibration.** I labelled 16 reports (one per case per arm, from the after runs) on the four judge criteria. The judge agreed on 63 of 64 verdicts and gave identical verdicts when re-run. The one disagreement was next steps on `human-misleading-cause`: the judge failed it for putting the rollback second, and I passed it. I passed all 64, so this shows the judge doesn't fail good reports, not that it catches bad ones; that needs labelled reports that should fail, such as ones from before the red-herring fix. The "mitigation first" rubric line is stricter than I am and should be relaxed rather than the agent changed.

## Before and after

In the first eval runs with the judge, the agent ruled out the inventory red herring in 7 of 18 runs (0.39) in both arms, and in only 1 of the 6 monitor-alert runs. The traces showed it filtering by service from its first query and never looking at the other services. Retrieval didn't help, because the agent searched past incidents using the main incident's symptoms, so INC-287 only came back when the alert itself mentioned inventory.

I added `summarize_log_patterns` and a line in the system prompt asking the agent to either connect warnings and errors in other services to the incident or rule them out. I then reran both arms: 8 cases, 3 repetitions each, `gpt-6.1-sol` as the agent and `claude-opus-5-5` as the judge.

| Metric | Baseline before | Baseline after | RAG before | RAG after |
| --- | --- | --- | --- | --- |
| Red herring ruled out | 0.39 | 1.00 | 0.39 | 1.00 |
| Alert verdict correct | 0.96 | 1.00 | 0.96 | 1.00 |
| Root cause correct | 0.95 | 0.95 | 0.86 | 1.00 |
| Ticket decision correct | n/a | 0.96 | n/a | 1.00 |
| Judge: next steps actionable | 0.88 | 0.83 | 0.83 | 0.67 |
| Tool calls per run | 6.38 | 5.92 | 6.38 | 6.29 |

Before: `triage-baseline-4abd667e`, `triage-rag-b7871ffb`. After: `triage-baseline-3923228f`, `triage-rag-18ddaf9a`.

The red herring is now ruled out in every run that tests it. The agent compares the inventory warnings before and during the incident, finds the same rate of about one a minute, and rules them out. Tool calls didn't go up.
