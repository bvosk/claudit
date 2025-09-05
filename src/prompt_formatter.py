import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
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

    def _format_timestamp(self) -> str:
        """Format timestamp from JSON data."""
        timestamp_str = self.json_data.get("timestamp", "")
        if timestamp_str:
            try:
                # Parse ISO timestamp and format it nicely
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except ValueError:
                return timestamp_str
        return "N/A"

    def _get_model(self) -> str:
        """Extract model name from request content."""
        return self.request_content.get("model", "Unknown")

    def _get_duration(self) -> Optional[float]:
        """Calculate duration if available."""
        return self.json_data.get("duration_ms")

    def _get_system_prompts(self) -> list:
        """Extract system prompts from request content."""
        return self.request_content.get("system", [])

    def _get_tools(self) -> list:
        """Extract tools from request content."""
        return self.request_content.get("tools", [])

    def _get_messages(self) -> list:
        """Extract messages from request content."""
        return self.request_content.get("messages", [])

    def _get_response(self) -> Optional[Dict[str, Any]]:
        """Extract response data if available."""
        return self.json_data.get("response")

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

            # Set up Jinja2 environment
            project_root = Path(__file__).parent.parent
            template_dir = project_root / "templates"

            if not template_dir.exists():
                raise FileNotFoundError(f"Template directory not found: {template_dir}")

            env = Environment(loader=FileSystemLoader(str(template_dir)))
            template = env.get_template("prompt_template.md")

            # Prepare template data
            template_data = {
                "timestamp": self._format_timestamp(),
                "model": self._get_model(),
                "duration": self._get_duration(),
                "system": self._get_system_prompts(),
                "tools": self._get_tools(),
                "messages": self._get_messages(),
                "response": self._get_response(),
            }

            # Render template
            rendered_content = template.render(**template_data)

            # Write to file
            output_path = prompts_dir / output_filename
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_content)

            self.logger.info(f"Generated markdown file: {output_path}")
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
