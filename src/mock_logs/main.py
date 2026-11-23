from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from mock_logs.generator import generate_archive
from mock_logs.scenarios import SCENARIOS


DEFAULT_SEED = 42
DEFAULT_OUTPUT_DIR = Path("data/datadog_logs")


def main(argv: Sequence[str] | None = None) -> None:
    parser = ArgumentParser(description="Generate mock Datadog log archives for each incident scenario")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    arguments = parser.parse_args(argv)

    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    for name, scenario in SCENARIOS.items():
        archive = generate_archive(scenario, seed=arguments.seed)
        (arguments.output_dir / f"{name}.json").write_text(archive.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
