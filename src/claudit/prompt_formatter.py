import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from claudit.models import Prompt


def render_prompt_markdown(prompt: Prompt) -> str:
    logger = logging.getLogger(__name__)

    template_dir = _find_template_directory()

    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("claudecode.md")

    template_data = {
        "system": prompt.system,
        "tools": prompt.tools,
    }

    try:
        rendered_content = template.render(**template_data)
    except Exception as e:
        logger.error("Template rendering failed: %s", e)
        raise

    return rendered_content


# Legacy functions removed - no longer needed since we get data directly from Prompt object


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


# _get_system_prompts and _get_tools functions removed - data comes directly from Prompt object


__all__ = ["render_prompt_markdown"]
