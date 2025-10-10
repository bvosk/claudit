"""Tests for AgentClient"""

import json
import subprocess
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from claudit.agent_client import AgentClient
from claudit.agents.base import CommandSpec
from claudit.models import Prompt


class _DummyStrategy:
    name = "dummy"

    def __init__(self, version_spec: CommandSpec | None):
        self._version_spec = version_spec

    def command(self) -> CommandSpec:
        return CommandSpec(
            command="echo main",
            use_shell=True,
            timeout_seconds=12.0,
        )

    def version_command(self) -> CommandSpec | None:
        return self._version_spec

    def environment_overrides(self, proxy_port: int) -> dict[str, str]:
        return {"DUMMY_PROXY_PORT": str(proxy_port)}

    def api_hosts(self):
        return ()

    def api_path_prefixes(self):
        return ()

    def scrub_cli_output(self, text: str) -> str:
        return text

    def extract_prompt(self, captured_data):
        return Prompt(system=[], tools=[], timestamp=datetime.now(timezone.utc), metadata={})


class TestAgentClientExtractPrompt:
    """Test suite for AgentClient.extract_prompt method"""

    def test_extract_prompt_basic(self):
        captured_data = [
            {
                "id": 1,
                "timestamp": "2025-01-01T12:00:00Z",
                "request": {
                    "method": "POST",
                    "url": "https://api.anthropic.com/v1/messages",
                    "content": {
                        "system": [
                            {"type": "text", "text": "You are a helpful assistant."}
                        ],
                        "tools": [{"name": "test_tool", "description": "A test tool"}],
                    },
                },
            }
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        assert isinstance(result, Prompt)
        assert len(result.system) == 1
        assert result.system[0]["type"] == "text"
        assert result.system[0]["text"] == "You are a helpful assistant."
        assert len(result.tools) == 1
        assert result.tools[0]["name"] == "test_tool"
        assert result.metadata is not None
        assert result.metadata["source"] == "claude_code"
        assert result.metadata["capture_id"] == 1

    def test_extract_prompt_with_string_content(self):
        content_dict = {
            "system": [{"type": "text", "text": "System prompt"}],
            "tools": [],
        }
        captured_data = [
            {
                "id": 1,
                "timestamp": "2025-01-01T12:00:00",
                "request": {
                    "method": "POST",
                    "url": "https://api.anthropic.com/v1/messages",
                    "content": json.dumps(content_dict),
                },
            }
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        assert len(result.system) == 1
        assert result.system[0]["text"] == "System prompt"
        assert result.tools == []

    def test_extract_prompt_empty_data(self):
        client = AgentClient()

        with pytest.raises(ValueError, match="No captured data provided"):
            client.extract_prompt([])

    def test_extract_prompt_malformed_json(self):
        captured_data = [
            {
                "id": 1,
                "timestamp": "2025-01-01T12:00:00",
                "request": {"content": "invalid json{"},
            }
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        assert result.system == []
        assert result.tools == []

    def test_extract_prompt_non_dict_content(self):
        captured_data = [
            {
                "id": 1,
                "request": {"content": '"just a string"'},
            }
        ]

        client = AgentClient()

        with pytest.raises(ValueError, match="Request content is not valid JSON"):
            client.extract_prompt(captured_data)

    def test_extract_prompt_missing_system_tools(self):
        captured_data = [
            {
                "id": 1,
                "request": {
                    "content": {"other_field": "value"}
                },
            }
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        assert result.system == []
        assert result.tools == []

    def test_extract_prompt_invalid_system_type(self):
        captured_data = [
            {
                "id": 1,
                "request": {
                    "content": {"system": "not a list", "tools": "also not a list"}
                },
            }
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        assert result.system == []
        assert result.tools == []

    def test_extract_prompt_timestamp_parsing(self):
        captured_data = [
            {
                "id": 1,
                "timestamp": "2025-01-01T12:00:00Z",
                "request": {"content": {"system": [{"type": "text", "text": "test"}]}},
            }
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        expected_time = datetime.fromisoformat("2025-01-01T12:00:00+00:00")
        assert result.timestamp == expected_time

    def test_extract_prompt_invalid_timestamp(self):
        with patch("claudit.agents.claude_code.strategy.datetime") as mock_dt:
            mock_now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.fromisoformat = datetime.fromisoformat

            captured_data = [
                {
                    "id": 1,
                    "timestamp": "invalid-timestamp",
                    "request": {
                        "content": {"system": [{"type": "text", "text": "test"}]}
                    },
                }
            ]

            client = AgentClient()
            result = client.extract_prompt(captured_data)

        assert result.timestamp == mock_now

    def test_extract_prompt_missing_timestamp(self):
        with patch("claudit.agents.claude_code.strategy.datetime") as mock_dt:
            mock_now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now

            captured_data = [
                {
                    "id": 1,
                    "request": {
                        "content": {"system": [{"type": "text", "text": "test"}]}
                    },
                }
            ]

            client = AgentClient()
            result = client.extract_prompt(captured_data)

        assert result.timestamp == mock_now


class TestAgentClientRunCommand:
    def test_run_agent_command_uses_strategy_version_command(self):
        version_spec = CommandSpec(
            command="tool --version",
            use_shell=False,
            timeout_seconds=7.0,
        )
        strategy = _DummyStrategy(version_spec=version_spec)
        client = AgentClient(strategy=strategy)

        with patch("claudit.agent_client.subprocess.run") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=version_spec.command,
                    returncode=0,
                    stdout="1.2.3\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args="echo main",
                    returncode=0,
                    stdout="done",
                    stderr="",
                ),
            ]

            result = client.run_agent_command()

        assert mock_run.call_count == 2

        version_call = mock_run.call_args_list[0]
        assert version_call.args[0] == version_spec.command
        assert version_call.kwargs["shell"] is version_spec.use_shell
        assert version_call.kwargs["timeout"] == version_spec.timeout_seconds
        assert version_call.kwargs["env"]["DUMMY_PROXY_PORT"] == str(client.proxy_port)

        main_call = mock_run.call_args_list[1]
        assert main_call.args[0] == "echo main"
        assert main_call.kwargs["shell"] is True
        assert main_call.kwargs["timeout"] == strategy.command().timeout_seconds
        assert result["command"] == "echo main"

    def test_run_agent_command_skips_preflight_when_strategy_has_no_version(self):
        strategy = _DummyStrategy(version_spec=None)
        client = AgentClient(strategy=strategy)

        with patch("claudit.agent_client.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args="echo main",
                returncode=0,
                stdout="done",
                stderr="",
            )

            client.run_agent_command()

        assert mock_run.call_count == 1
        call = mock_run.call_args_list[0]
        assert call.args[0] == "echo main"

    def test_extract_prompt_metadata_complete(self):
        captured_data = [
            {
                "id": 42,
                "request": {
                    "method": "POST",
                    "url": "https://api.anthropic.com/v1/messages",
                    "content": {"system": [{"type": "text", "text": "test"}]},
                },
            }
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        assert result.metadata is not None
        assert result.metadata["source"] == "claude_code"
        assert result.metadata["capture_id"] == 42
        assert result.metadata["request_url"] == "https://api.anthropic.com/v1/messages"
        assert result.metadata["request_method"] == "POST"

    def test_extract_prompt_multiple_captures_uses_first(self):
        captured_data = [
            {
                "id": 2,
                "request": {
                    "content": {"system": [{"type": "text", "text": "Second capture"}]}
                },
            },
            {
                "id": 1,
                "request": {
                    "content": {"system": [{"type": "text", "text": "First capture"}]}
                },
            },
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        assert result.system[0]["text"] == "Second capture"
        assert result.metadata is not None
        assert result.metadata["capture_id"] == 2

    def test_extract_prompt_creates_valid_prompt_object(self):
        captured_data = [
            {
                "id": 1,
                "request": {
                    "content": {
                        "system": [{"type": "text", "text": "Valid system message"}],
                        "tools": [{"name": "valid_tool"}],
                    }
                },
            }
        ]

        client = AgentClient()
        result = client.extract_prompt(captured_data)

        result.validate()
        assert isinstance(result, Prompt)
