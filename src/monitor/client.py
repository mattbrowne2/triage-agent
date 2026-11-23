import httpx

from incident_triage.models.alert import Alert
from monitor.models import Delivery


CONNECT_RETRIES = 3
TIMEOUT_SECONDS = 10.0


def build_client(api_url: str) -> httpx.Client:
    return httpx.Client(
        base_url=api_url, transport=httpx.HTTPTransport(retries=CONNECT_RETRIES), timeout=TIMEOUT_SECONDS
    )


def send_alert(client: httpx.Client, alert: Alert) -> Delivery:
    try:
        response = client.post("/alerts", json=alert.model_dump(mode="json"))
    except httpx.TransportError as error:
        return Delivery(alert_id=alert.id, delivered=False, detail=f"{type(error).__name__}: {error}")
    return Delivery(alert_id=alert.id, delivered=response.is_success, detail=f"HTTP {response.status_code}")
