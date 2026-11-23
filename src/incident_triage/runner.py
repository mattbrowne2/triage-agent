from collections.abc import Iterator

from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph

from incident_triage.models.triage_report import TriageReport


def stream_triage(agent: CompiledStateGraph, alert: str, max_steps: int) -> Iterator[AnyMessage | TriageReport]:
    try:
        for update in agent.stream(
            {"messages": [HumanMessage(content=alert)]},
            config={"recursion_limit": max_steps},
            stream_mode="updates",
        ):
            for node_update in update.values():
                yield from node_update["messages"]
                match node_update:
                    case {"structured_response": TriageReport() as report}:
                        yield report
    except GraphRecursionError:
        yield AIMessage(content=f"Triage stopped after {max_steps} steps without reaching a conclusion.")
    except StructuredOutputValidationError as error:
        yield AIMessage(content=f"Triage ended without a valid report: {error}")
