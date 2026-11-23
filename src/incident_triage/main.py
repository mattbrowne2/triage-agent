from argparse import ArgumentParser

from incident_triage.models.triage_report import TriageReport
from incident_triage.runner import stream_triage
from incident_triage.settings import get_settings
from incident_triage.wiring import alert_key_for, build_agent_factory


_settings = get_settings()


def main() -> None:
    parser = ArgumentParser(description="Triage a production alert against Datadog logs")
    parser.add_argument(
        "alert", help="Alert text, e.g. 'ALR-8812: checkout-service 5xx error rate 18%% since 02:09 UTC'"
    )
    arguments = parser.parse_args()

    agent = build_agent_factory(_settings)(alert_key_for(arguments.alert))

    for item in stream_triage(agent, arguments.alert, _settings.MAX_AGENT_STEPS):
        match item:
            case TriageReport():
                print(item.model_dump_json(indent=2))
            case _:
                item.pretty_print()


if __name__ == "__main__":
    main()
