from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Sequence

from claudit.agents.agent_strategy import AgentStrategy, CommandSpec
from claudit.models import Prompt


class ClaudeCodeStrategy(AgentStrategy):
    """Agent strategy encapsulating current Claude Code CLI behaviour."""

    name = "claudecode"
    USER_PROMPT = "hello"

    def command(self) -> CommandSpec:
        return CommandSpec(
            command=f"claude -p {self.USER_PROMPT} --model haiku",
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

    def extract_prompt(self, captured_data: List[Dict[str, Any]]) -> Prompt:
        if not captured_data:
            raise ValueError("No captured data provided")

        target_prompt = self.USER_PROMPT
        invalid_content = False

        for capture in captured_data:
            request_data = capture.get("request", {})
            request_content = request_data.get("content", {})
            request_content = self._ensure_dict_content(request_content)

            if request_content is None:
                invalid_content = True
                continue

            message_texts = self._user_message_texts(request_content)
            if any(text == target_prompt for text in message_texts):
                system_prompts = self._normalize_system_entries(
                    request_content.get("system", [])
                )
                tools = request_content.get("tools", [])
                if not isinstance(tools, list):
                    tools = []
                return Prompt(system=system_prompts, tools=tools)

        if invalid_content:
            raise ValueError("Request content is not valid JSON")

        raise ValueError(
            f"Failed to locate captured request containing expected user prompt: {target_prompt}"
        )

    def scrub_prompt(self, prompt: Prompt) -> Prompt:
        """Agent-specific prompt scrubbing for Claude Code."""
        return Prompt(
            system=[self._scrub_text_content(s) for s in prompt.system],
            tools=[self._scrub_value(t) for t in prompt.tools],
        )

    def _scrub_value(self, data: Any) -> Any:
        if isinstance(data, str):
            return self._scrub_text_content(data)
        if isinstance(data, dict):
            return {k: self._scrub_value(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._scrub_value(i) for i in data]
        return copy.deepcopy(data)

    def _scrub_text_content(self, text: str) -> str:
        if not text:
            return text
        today = datetime.now().strftime("%Y-%m-%d")
        if today:
            return text.replace(f"Today's date: {today}", "Today's date: [date]")
        return text

    def _normalize_system_entries(self, raw_system: Any) -> List[str]:
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

        return system_prompts

    def _ensure_dict_content(self, request_content: Any) -> Dict[str, Any] | None:
        if isinstance(request_content, str):
            try:
                request_content = json.loads(request_content)
            except json.JSONDecodeError:
                return None

        if request_content is None:
            return {}

        if not isinstance(request_content, dict):
            return None
        return request_content

    def _user_message_texts(self, request_content: Dict[str, Any]) -> List[str]:
        messages = request_content.get("messages")
        if not isinstance(messages, list) or not messages:
            return []

        first = messages[0]
        if not isinstance(first, dict):
            return []

        if first.get("role") != "user":
            return []

        content = first.get("content")
        texts: List[str] = []
        if isinstance(content, str):
            stripped = content.strip()
            if stripped:
                texts.append(stripped)

        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text = part["text"].strip()
                    if text:
                        texts.append(text)
                elif isinstance(part, str):
                    stripped = part.strip()
                    if stripped:
                        texts.append(stripped)

        return texts
