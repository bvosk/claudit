import json
import logging
import re
import datetime
from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader

from models import CapturedRequest


def render_prompt_markdown(captured_request: CapturedRequest) -> str:
    logger = logging.getLogger(__name__)

    request_content = _extract_request_content(captured_request)
    template_dir = _find_template_directory()

    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("claudecode.md")

    template_data = {
        "system": _get_system_prompts(request_content),
        "tools": _get_tools(request_content),
    }

    try:
        rendered_content = template.render(**template_data)
    except Exception as e:
        logger.error("Template rendering failed: %s", e)
        raise

    return _scrub_content(rendered_content)


def _extract_request_content(captured_request: CapturedRequest) -> Dict[str, Any]:
    body = captured_request.request_body
    if isinstance(body, dict):
        return body
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse request content as JSON: {e}") from e
    raise ValueError("Request body is not parseable JSON")


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


def _get_system_prompts(request_content: Dict[str, Any]) -> list:
    return request_content.get("system", [])


def _get_tools(request_content: Dict[str, Any]) -> list:
    return request_content.get("tools", [])


_DATE_PATTERN_PREFIX = "Today's date: "


def _scrub_content(content: str) -> str:
    today = datetime.date.today().strftime("%Y-%m-%d")
    if today:
        content = re.sub(
            re.escape(f"{_DATE_PATTERN_PREFIX}{today}"),
            f"{_DATE_PATTERN_PREFIX}[date]",
            content,
        )
    return content


__all__ = ["render_prompt_markdown"]
