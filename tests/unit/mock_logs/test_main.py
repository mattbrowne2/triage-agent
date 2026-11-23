from pathlib import Path

from incident_triage.models.datadog import LogArchive
from mock_logs.generator import generate_archive
from mock_logs.main import DEFAULT_SEED, main
from mock_logs.scenarios import SCENARIOS


def test_main_writes_one_archive_per_scenario(tmp_path: Path) -> None:
    main(["--output-dir", str(tmp_path)])

    assert {path.name: LogArchive.model_validate_json(path.read_text()) for path in tmp_path.iterdir()} == {
        f"{name}.json": generate_archive(scenario, seed=DEFAULT_SEED) for name, scenario in SCENARIOS.items()
    }
