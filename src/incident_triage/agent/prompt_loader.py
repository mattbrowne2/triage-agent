from pathlib import Path


PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_system_prompt() -> str:
    return (PROMPTS_DIR / "system_prompt.md").read_text().strip()
