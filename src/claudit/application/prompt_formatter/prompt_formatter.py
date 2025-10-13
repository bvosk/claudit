import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from claudit.models import Prompt

DEFAULT_TEMPLATE_PATH = Path(__file__).parent / "template.md"


class PromptFormatter:
    def __init__(self, template_path: str | Path):
        self._logger = logging.getLogger(__name__)
        self._template_path = Path(template_path)

        if not self._template_path.exists():
            raise FileNotFoundError(
                f"Template file not found at {self._template_path}"
            )

        self._environment = Environment(
            loader=FileSystemLoader(str(self._template_path.parent))
        )
        self._template_name = self._template_path.name

    def render(self, prompt: Prompt) -> str:
        system_messages = [
            {"type": "text", "text": entry if isinstance(entry, str) else str(entry)}
            for entry in prompt.system
        ]

        template = self._environment.get_template(self._template_name)

        template_data = {
            "system": system_messages,
            "tools": prompt.tools,
        }

        try:
            return template.render(**template_data)
        except Exception as exc:
            self._logger.error("Template rendering failed: %s", exc)
            raise
