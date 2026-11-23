from pathlib import Path

from incident_triage.models.tools import ToolName


DESCRIPTIONS_DIR = Path(__file__).parent / "descriptions"


def load_tool_description(tool_name: ToolName) -> str:
    return (DESCRIPTIONS_DIR / f"{tool_name}.md").read_text().strip()
