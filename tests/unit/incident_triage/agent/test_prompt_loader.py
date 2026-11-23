from pathlib import Path

from incident_triage.agent.prompt_loader import load_system_prompt


PROMPTS_DIR = Path(__file__).parents[4] / "src" / "incident_triage" / "agent" / "prompts"


def test_system_prompt_is_read_from_prompts_directory() -> None:
    assert load_system_prompt() == (PROMPTS_DIR / "system_prompt.md").read_text().strip()


def test_system_prompt_treats_past_incidents_as_precedent_not_evidence() -> None:
    assert (
        "- Past incidents are precedent, not evidence. Confirm a past cause in the current logs before relying on it."
        in load_system_prompt().splitlines()
    )


def test_system_prompt_requires_other_services_anomalies_to_be_connected_or_ruled_out() -> None:
    assert (
        "- Account for every other service showing warnings or errors around the incident: connect it to the "
        "incident or rule it out, citing the evidence." in load_system_prompt().splitlines()
    )


def test_system_prompt_files_one_ticket_only_for_a_confirmed_incident() -> None:
    assert (
        "- When the logs confirm an incident that needs on-call attention, file one Jira ticket for it before you "
        "report. Never file one when the logs show no incident." in load_system_prompt().splitlines()
    )
