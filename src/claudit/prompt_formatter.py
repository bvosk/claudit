import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from claudit.models import Prompt


def render_prompt_markdown(prompt: Prompt) -> str:
    logger = logging.getLogger(__name__)

    template_dir = _find_template_directory()

    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("claudecode.md")

    system_messages = [
        {"type": "text", "text": entry if isinstance(entry, str) else str(entry)}
        for entry in prompt.system
    ]

    template_data = {
        "system": system_messages,
        "tools": prompt.tools,
    }

    try:
        rendered_content = template.render(**template_data)
    except Exception as e:
        logger.error("Template rendering failed: %s", e)
        raise

    return rendered_content


def _find_template_directory() -> Path:
    candidates = [
        Path(__file__).parent.parent / "templates",
        Path("/app/templates"),
        Path.cwd() / "templates",
    ]

    for directory in candidates:
        if (directory / "claudecode.md").exists():
            return directory

    raise FileNotFoundError(
        "Template directory not found (searched: "
        + ", ".join(str(p) for p in candidates)
        + ")"
    )


__all__ = ["render_prompt_markdown"]
