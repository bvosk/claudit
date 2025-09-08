import json
import logging
import re
import datetime
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader


class PromptFormatter:
    def __init__(self, json_data: Dict[str, Any]):
        self.json_data = json_data
        self.request_content = self._parse_request_content()
        self.logger = logging.getLogger(__name__)

    def _parse_request_content(self) -> Dict[str, Any]:
        """Parse the request content from JSON data."""
        try:
            if "request" in self.json_data and "content" in self.json_data["request"]:
                content = self.json_data["request"]["content"]
                if isinstance(content, str):
                    return json.loads(content)
                return content
            else:
                raise ValueError("Invalid JSON structure: missing request.content")
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse request content as JSON: {e}")
            raise ValueError(f"Failed to parse request content as JSON: {e}")

    def _get_system_prompts(self) -> list:
        """Extract system prompts from request content."""
        return self.request_content.get("system", [])

    def _get_tools(self) -> list:
        """Extract tools from request content."""
        return self.request_content.get("tools", [])

    def _scrub_content(self, content: str) -> str:
        """Scrub sensitive or unwanted information from the content."""
        today = datetime.date.today().strftime("%Y-%m-%d")
        content = re.sub(r"Today's date: " + today, "Today's date: [date]", content)
        return content

    def format_to_markdown(self, output_filename: str = "claudecode.md") -> str:
        """
        Generate markdown file in prompts directory using jinja2 template.

        Args:
            output_filename: Name of the output file (default: claudecode.md)

        Returns:
            Path to the generated markdown file
        """
        try:
            # Create prompts directory if it doesn't exist
            prompts_dir = Path("prompts")
            prompts_dir.mkdir(exist_ok=True)

            # Set up Jinja2 environment - find templates directory
            # Try multiple possible locations for templates
            possible_template_dirs = [
                Path(__file__).parent.parent
                / "templates",  # Development: src/../templates
                Path("/app/templates"),  # Docker: /app/templates
                Path.cwd() / "templates",  # Current working directory
            ]

            template_dir = None
            for dir_path in possible_template_dirs:
                if dir_path.exists():
                    template_dir = dir_path
                    break

            if template_dir is None:
                available_dirs = [str(d) for d in possible_template_dirs]
                raise FileNotFoundError(
                    f"Template directory not found in any of: {available_dirs}"
                )

            if not template_dir.exists():
                raise FileNotFoundError(f"Template directory not found: {template_dir}")

            env = Environment(loader=FileSystemLoader(str(template_dir)))
            template = env.get_template("claudecode.md")

            # Prepare template data
            template_data = {
                "system": self._get_system_prompts(),
                "tools": self._get_tools(),
            }

            # Render template
            rendered_content = template.render(**template_data)

            # Scrub unwanted content
            rendered_content = self._scrub_content(rendered_content)

            # Write to file
            output_path = prompts_dir / output_filename
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_content)

            return str(output_path)

        except Exception as e:
            self.logger.error(f"Error generating markdown: {e}")
            raise


def format_captured_prompt(
    json_file_path: str, output_filename: str = "claudecode.md"
) -> str:
    """
    Convenience function to format a captured prompt JSON file to markdown.

    Args:
        json_file_path: Path to the JSON file containing captured prompt data
        output_filename: Name of the output markdown file

    Returns:
        Path to the generated markdown file
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    formatter = PromptFormatter(json_data)
    return formatter.format_to_markdown(output_filename)
