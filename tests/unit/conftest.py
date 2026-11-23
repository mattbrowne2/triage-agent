import os


os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["INCIDENT_SEARCH_ENABLED"] = "false"

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolCall
from langchain_core.outputs import ChatResult
from langchain_core.tools import BaseTool, StructuredTool

from incident_triage.agent.triage_agent import build_triage_agent
from incident_triage.incident_store.index import IncidentIndex
from incident_triage.jira.store import JiraStore
from incident_triage.log_store.repository import LogRepository
from incident_triage.models.alert import Alert
from incident_triage.models.datadog import Log, LogArchive, LogAttributes, LogStatus
from incident_triage.models.incident import ChangeKind, ChangeLink, PastIncident, Resolution
from incident_triage.models.jira import JiraPriority, TicketRequest
from incident_triage.models.triage_report import Confidence, RelatedIncident, TriageReport
from incident_triage.settings import LLMProvider
from incident_triage.tools.create_jira_ticket import build_create_jira_ticket_tool
from incident_triage.tools.query_logs import build_query_logs_tool
from incident_triage.tools.search_past_incidents import build_search_past_incidents_tool
from incident_triage.tools.summarize_log_patterns import build_summarize_log_patterns_tool
from triage_api.app import create_app


class ScriptedChatModel(GenericFakeChatModel):
    bound_kwargs: dict[str, Any] = {}

    def bind_tools(
        self, tools: Sequence[BaseTool | Callable[..., Any] | dict[str, Any]], **kwargs: Any
    ) -> "ScriptedChatModel":
        self.bound_kwargs = kwargs
        return self


class UnreachableChatModel(ScriptedChatModel):
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise ConnectionError("provider unreachable")


@pytest.fixture
def unreachable_chat_model() -> UnreachableChatModel:
    return UnreachableChatModel(messages=iter(()))


@pytest.fixture
def optional_settings_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_REASONING_EFFORT",
        "MAX_AGENT_STEPS",
        "DATADOG_LOGS_PATH",
        "INCIDENTS_PATH",
        "EMBEDDING_MODEL",
        "INCIDENT_SEARCH_ENABLED",
        "INCIDENT_MIN_SIMILARITY",
        "JUDGE_PROVIDER",
        "JUDGE_MODEL",
        "JIRA_TICKETS_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def scripted_chat_model_factory() -> Callable[..., ScriptedChatModel]:
    def build(*responses: AIMessage) -> ScriptedChatModel:
        return ScriptedChatModel(messages=iter(responses))

    return build


@pytest.fixture
def checkout_error_rate_alert() -> Alert:
    return Alert(
        id="error-rate:checkout-service:2026-11-17T02:05:00Z",
        monitor="error-rate",
        service="checkout-service",
        window_start=datetime(2026, 11, 17, 2, 5, tzinfo=UTC),
        window_end=datetime(2026, 11, 17, 2, 10, tzinfo=UTC),
        error_count=15,
        log_count=45,
        threshold=0.05,
    )


@pytest.fixture
def confirmed_triage_report() -> TriageReport:
    return TriageReport(
        alert_confirmed=True,
        alert_discrepancy=None,
        root_cause="payment-service v2.14.0 rejects the currency_code field sent by checkout-service",
        confidence=Confidence.HIGH,
        evidence=["02:10:04 checkout-service: PaymentClientError: 400 Bad Request - unknown field 'currency_code'"],
        impact="Checkout requests failing since 02:09 UTC",
        next_steps=["Roll back payment-service to v2.13.2"],
        ruled_out=["inventory-service timeouts, present before the incident"],
        ticket_key="OPS-1",
        related_incidents=[
            RelatedIncident(
                key="INC-311",
                why_similar="A payment-service deploy changed the charge request schema and checkout's calls got 400s",
                what_differs="This time the field is currency_code and the version is v2.14.0",
                change_urls=["https://git.example.com/payments/pull/1432"],
            )
        ],
    )


@pytest.fixture
def report_submission_factory() -> Callable[[TriageReport], AIMessage]:
    def build(report: TriageReport) -> AIMessage:
        return AIMessage(content=report.model_dump_json())

    return build


@pytest.fixture
def report_tool_call_factory() -> Callable[[TriageReport], AIMessage]:
    def build(report: TriageReport) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[ToolCall(name="TriageReport", args=report.model_dump(mode="json"), id="report_1")],
        )

    return build


@pytest.fixture
def checkout_payment_error_log() -> Log:
    return Log(
        id="AAAAAZcheckout01",
        attributes=LogAttributes(
            timestamp=datetime(2026, 11, 17, 2, 10, 4, tzinfo=UTC),
            status=LogStatus.ERROR,
            service="checkout-service",
            host="checkout-service-7d9f-x2k4p",
            message="PaymentClientError: 400 Bad Request - unknown field 'currency_code'",
            tags=["env:prod", "service:checkout-service", "version:3.8.1"],
            attributes={"trace_id": "7f3a9c2e", "http": {"status_code": 500}},
        ),
    )


@pytest.fixture
def checkout_order_info_log() -> Log:
    return Log(
        id="AAAAAZcheckout02",
        attributes=LogAttributes(
            timestamp=datetime(2026, 11, 17, 2, 1, 30, tzinfo=UTC),
            status=LogStatus.INFO,
            service="checkout-service",
            host="checkout-service-7d9f-x2k4p",
            message="Order placed successfully",
            tags=["env:prod", "service:checkout-service", "version:3.8.1"],
            attributes={"trace_id": "1b2c3d4e"},
        ),
    )


@pytest.fixture
def payment_deploy_log() -> Log:
    return Log(
        id="AAAAAZpayment01",
        attributes=LogAttributes(
            timestamp=datetime(2026, 11, 17, 2, 8, 47, tzinfo=UTC),
            status=LogStatus.INFO,
            service="payment-service",
            host="payment-service-5c8b-q9m2z",
            message="Rolling update complete: payment-service v2.14.0",
            tags=["env:prod", "service:payment-service", "version:2.14.0"],
            attributes={},
        ),
    )


@pytest.fixture
def log_archive(checkout_payment_error_log: Log, checkout_order_info_log: Log, payment_deploy_log: Log) -> LogArchive:
    return LogArchive(data=[checkout_order_info_log, payment_deploy_log, checkout_payment_error_log])


@pytest.fixture
def log_repository(log_archive: LogArchive) -> LogRepository:
    return LogRepository(log_archive)


@pytest.fixture
def query_logs_tool(log_repository: LogRepository) -> StructuredTool:
    return build_query_logs_tool(log_repository)


@pytest.fixture
def summarize_log_patterns_tool(log_repository: LogRepository) -> StructuredTool:
    return build_summarize_log_patterns_tool(log_repository)


@pytest.fixture
def triage_client_factory(
    scripted_chat_model_factory: Callable[..., BaseChatModel], query_logs_tool: StructuredTool
) -> Callable[..., TestClient]:
    def build(*responses: AIMessage) -> TestClient:
        agent = build_triage_agent(scripted_chat_model_factory(*responses), [query_logs_tool], LLMProvider.ANTHROPIC)
        return TestClient(create_app(lambda alert_key: agent, max_steps=10), base_url="http://triage-api")

    return build


@pytest.fixture
def resolved_contract_incident() -> PastIncident:
    return PastIncident(
        key="INC-311",
        title="Checkout failing after payment-service deploy made a request field required",
        service="checkout-service",
        symptoms=(
            "checkout-service returned HTTP 500. PaymentClientError: 400 Bad Request - missing field 'amount_minor'."
        ),
        opened_at=datetime(2026, 9, 2, 14, 20, tzinfo=UTC),
        resolution=Resolution(
            confirmed_root_cause="payment-service v2.11.0 made 'amount_minor' required",
            fix="Rolled payment-service back to v2.10.4, then released v2.11.1 with the field optional",
            changes=[
                ChangeLink(kind=ChangeKind.ROLLBACK, ref="deploy #7731", url="https://ci.example.com/deploys/7731"),
                ChangeLink(
                    kind=ChangeKind.PULL_REQUEST,
                    ref="payments#1432",
                    url="https://git.example.com/payments/pull/1432",
                ),
            ],
            resolved_at=datetime(2026, 9, 2, 14, 48, tzinfo=UTC),
            agent_was_right=None,
        ),
    )


@pytest.fixture
def open_load_balancer_incident() -> PastIncident:
    return PastIncident(
        key="INC-316",
        title="Intermittent 502s from the load balancer in front of web-frontend",
        service="web-frontend",
        symptoms="web-frontend returned occasional HTTP 502 Bad Gateway responses. Not yet explained.",
        opened_at=datetime(2026, 11, 12, 16, 45, tzinfo=UTC),
        resolution=None,
    )


@pytest.fixture
def fake_embeddings() -> DeterministicFakeEmbedding:
    return DeterministicFakeEmbedding(size=256)


@pytest.fixture
def incident_index(
    resolved_contract_incident: PastIncident,
    open_load_balancer_incident: PastIncident,
    fake_embeddings: DeterministicFakeEmbedding,
) -> IncidentIndex:
    return IncidentIndex([resolved_contract_incident, open_load_balancer_incident], fake_embeddings, min_similarity=0.5)


@pytest.fixture
def search_past_incidents_tool(incident_index: IncidentIndex) -> StructuredTool:
    return build_search_past_incidents_tool(incident_index)


@pytest.fixture
def jira_now() -> datetime:
    return datetime(2026, 11, 17, 2, 16, tzinfo=UTC)


@pytest.fixture
def jira_store(jira_now: datetime) -> JiraStore:
    return JiraStore(clock=lambda: jira_now, issues=[])


@pytest.fixture
def rollback_ticket_request() -> TicketRequest:
    return TicketRequest(
        summary="Checkout failing: payment-service v2.14.0 rejects currency_code",
        description="Since 02:09 UTC checkout-service gets 400 unknown field 'currency_code' from payment-service.",
        priority=JiraPriority.HIGHEST,
        service="payment-service",
    )


@pytest.fixture
def create_jira_ticket_tool(jira_store: JiraStore) -> StructuredTool:
    return build_create_jira_ticket_tool(jira_store, alert_key="error-rate:checkout-service:2026-11-17T02:05:00Z")
