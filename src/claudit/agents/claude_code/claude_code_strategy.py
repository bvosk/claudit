from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence

from claudit.agents.agent_strategy import AgentStrategy, CommandSpec
from claudit.models import Prompt


class ClaudeCodeStrategy(AgentStrategy):
    """Agent strategy encapsulating current Claude Code CLI behaviour."""

    name = "claudecode"

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

        request_content = request_data.get("content", {})
        if isinstance(request_content, str):
            try:
                request_content = json.loads(request_content)
            except json.JSONDecodeError:
                request_content = {}

        if not isinstance(request_content, dict):
            raise ValueError("Request content is not valid JSON")

        raw_system = request_content.get("system", [])
        if not isinstance(raw_system, list):
            raw_system = [raw_system] if raw_system else []

        system_prompts: List[str] = []
        for item in raw_system:
            if isinstance(item, str):
                system_prompts.append(item)
            elif isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    system_prompts.append(text_value)
                else:
                    system_prompts.append(json.dumps(item))
            else:
                system_prompts.append(str(item))

        tools = request_content.get("tools", [])
        if not isinstance(tools, list):
            tools = []

        return Prompt(system=system_prompts, tools=tools)
