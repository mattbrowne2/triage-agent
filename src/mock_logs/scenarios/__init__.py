from mock_logs.models import Scenario
from mock_logs.scenarios.payment_service_bad_deploy import PAYMENT_SERVICE_BAD_DEPLOY


SCENARIOS: dict[str, Scenario] = {scenario.name: scenario for scenario in (PAYMENT_SERVICE_BAD_DEPLOY,)}
