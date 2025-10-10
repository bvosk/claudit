from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

from claudit.agents.base import AgentStrategy, CommandSpec
from claudit.models import Prompt


class ClaudeCodeStrategy(AgentStrategy):
    """Agent strategy encapsulating current Claude Code CLI behaviour."""

    name = "claude_code"

    _TOOLS_BLOCK_PATTERN = re.compile(
        r"^You can use the following tools.*?:", re.MULTILINE
    )

    def command(self) -> CommandSpec:
        return CommandSpec(
            command="claude -p hello --model haiku",
            use_shell=True,
            timeout_seconds=15.0,
        )

    def version_command(self) -> CommandSpec | None:
        return CommandSpec(
            command="claude -v",
            use_shell=True,
            timeout_seconds=5.0,
        )

    def environment_overrides(self, proxy_port: int) -> Dict[str, str]:
        return {
            "ANTHROPIC_BASE_URL": f"http://localhost:{proxy_port}",
            "ANTHROPIC_API_KEY": "DUMMY",
        }

    def api_hosts(self) -> Sequence[str]:
        return ("api.anthropic.com",)

    def api_path_prefixes(self) -> Sequence[str]:
        return ("/v1/messages",)

    def scrub_cli_output(self, text: str) -> str:
        if not text:
            return text

        match = self._TOOLS_BLOCK_PATTERN.search(text)
        if not match:
            return text

        start = match.start()
        remainder = text[start:]
        split_index = remainder.find("\n\n")
        if split_index == -1:
            return text[:start].rstrip() + "\n"
        cleaned = text[:start] + remainder[split_index + 2 :]
        return cleaned.lstrip("\n")

    def extract_prompt(self, captured_data: List[Dict[str, Any]]) -> Prompt:
        if not captured_data:
            raise ValueError("No captured data provided")

        capture = captured_data[0]
        request_data = capture.get("request", {})

        timestamp_str = capture.get("timestamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        request_content = request_data.get("content", {})
        if isinstance(request_content, str):
            try:
                request_content = json.loads(request_content)
            except json.JSONDecodeError:
                request_content = {}

        if not isinstance(request_content, dict):
            raise ValueError("Request content is not valid JSON")

        system_messages = request_content.get("system", [])
        if not isinstance(system_messages, list):
            system_messages = []

        tools = request_content.get("tools", [])
        if not isinstance(tools, list):
            tools = []

        metadata = {
            "source": self.name,
            "capture_id": capture.get("id"),
            "request_url": request_data.get("url", ""),
            "request_method": request_data.get("method", ""),
        }

        return Prompt(system=system_messages, timestamp=timestamp, tools=tools, metadata=metadata)
