from incident_triage.models.incident import PastIncident


def incident_document(incident: PastIncident) -> str:
    lines = [incident.title, f"Service: {incident.service}", f"Symptoms: {incident.symptoms}"]
    match incident.resolution:
        case None:
            return "\n".join(lines)
        case resolution:
            return "\n".join([*lines, f"Confirmed root cause: {resolution.confirmed_root_cause}"])
