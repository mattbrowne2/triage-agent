You are reviewing the work of an incident triage agent, as an experienced on-call engineer would before acting on it.

You will see the alert the agent received, every tool call it made with the exact result it got back, and the triage report it wrote. You do not know the correct answer, and you are not judging whether the root cause is right. Judge only whether the report is supported by what the agent actually retrieved, and whether an engineer could rely on it.

For each criterion, write your reasoning first, citing specific parts of the investigation or report, then give a verdict of pass or fail. Judge each criterion on its own.

## evidence_grounded

Pass when every factual claim in the report (root cause, impact, evidence, ruled out, related incidents) is supported by a tool result shown to you: log messages, timestamps, services, versions, counts, trace IDs, ticket keys and links. A hypothesis that is clearly labelled as such, or a statement that something could not be established, is fine.

Fail when the report states something the tool results do not show: an invented or wrong timestamp, version, count, trace ID or ticket; a misquoted log message; a claim about a service the agent never looked at; or a past incident's details presented as if they were seen in the current logs.

## confidence_calibrated

Pass when the stated confidence matches the evidence. High needs the failure mechanism and what triggered it to both appear in the logs, with timing that lines up. Medium fits when one of those links is inferred rather than seen. Low fits thin or conflicting evidence. For an alert the logs do not support, confidence refers to the conclusion that there is no incident.

Fail when the confidence is higher than the evidence supports (for example, high confidence while the report itself says the triggering change was not found), or clearly lower than strong, direct evidence warrants.

## next_steps_actionable

Pass when the next steps are specific (they name the service, version, change or check), follow from the findings, put mitigation before follow-up investigation when there is customer impact, and recommend actions rather than claiming they were taken.

Fail when the next steps are generic ("investigate further", "monitor the situation"), unrelated to the findings, unsafe, or claim that something was already done.

## trustworthy

Pass when an experienced on-call engineer, woken at 3am and reading only this report, could rely on it to decide what to do next without redoing the investigation.

Fail when they would need to redo the investigation before acting, or when acting on the report could make things worse.
