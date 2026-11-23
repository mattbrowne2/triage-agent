from pathlib import Path

from incident_triage.models.incident import IncidentArchive, PastIncident


SEED_INCIDENTS = Path(__file__).parents[4] / "data" / "incidents" / "past_incidents.json"


def test_seed_incidents_load_with_resolved_and_open_tickets() -> None:
    archive = IncidentArchive.model_validate_json(SEED_INCIDENTS.read_text())

    assert [(incident.key, incident.resolution is None) for incident in archive.incidents] == [
        ("INC-311", False),
        ("INC-287", False),
        ("INC-298", False),
        ("INC-305", False),
        ("INC-276", False),
        ("INC-302", False),
        ("INC-316", True),
    ]


def test_past_incident_round_trips_through_json(resolved_contract_incident: PastIncident) -> None:
    assert PastIncident.model_validate_json(resolved_contract_incident.model_dump_json()) == resolved_contract_incident
