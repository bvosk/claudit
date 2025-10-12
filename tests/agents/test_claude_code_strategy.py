import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from claudit.agents.claude_code import ClaudeCodeStrategy


class TestClaudeCodeStrategyCommand:
    def test_command_spec_matches_current_cli_invocation(self):
        strategy = ClaudeCodeStrategy()
        spec = strategy.command()

        assert spec.command == "claude -p hello --model haiku"
        assert spec.use_shell is True
        assert spec.timeout_seconds == 15.0

    def test_version_command_spec_matches_preflight_invocation(self):
        strategy = ClaudeCodeStrategy()
        spec = strategy.version_command()

        assert spec is not None
        assert spec.command == "claude -v"
        assert spec.use_shell is True
        assert spec.timeout_seconds == 5.0

    def test_environment_overrides_include_proxy_base_and_dummy_key(self):
        strategy = ClaudeCodeStrategy()
        overrides = strategy.environment_overrides(9090)

        assert overrides["ANTHROPIC_BASE_URL"] == "http://localhost:9090"
        assert overrides["ANTHROPIC_API_KEY"] == "DUMMY"


class TestClaudeCodeStrategyScrubbing:
    def setup_method(self):
        self.strategy = ClaudeCodeStrategy()

    def test_scrubs_dynamic_tooling_block_with_trailing_blank(self):
        text = (
            "Intro line\n"
            "You can use the following tools:\n"
            "- file_browser\n"
            "- terminal\n"
            "\n"
            "Rest of instructions\n"
        )

        cleaned = self.strategy.scrub_cli_output(text)

        assert cleaned == "Intro line\nRest of instructions\n"

    def test_returns_original_text_when_no_tooling_block_present(self):
        text = "Intro line\nHelpful instructions\n"

        cleaned = self.strategy.scrub_cli_output(text)

        assert cleaned == text

    def test_scrubs_to_end_when_no_blank_line_terminator_found(self):
        text = (
            "Intro line\n" "You can use the following tools:\n" "- github\n" "- shell\n"
        )

        cleaned = self.strategy.scrub_cli_output(text)

        assert cleaned == "Intro line\n"


class TestClaudeCodeStrategyPromptExtraction:
    def setup_method(self):
        self.strategy = ClaudeCodeStrategy()

    def test_extract_prompt_parses_dict_payload(self):
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

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.metadata["source"] == self.strategy.name
        assert prompt.metadata["request_url"] == "https://api.anthropic.com/v1/messages"

    def test_extract_prompt_accepts_json_string_payload(self):
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

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.system[0]["text"] == "System prompt"

    def test_extract_prompt_invalid_timestamp_falls_back_to_now(self):
        strategy = ClaudeCodeStrategy()
        fake_now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        with patch(
            "claudit.agents.claude_code.claude_code_strategy.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.fromisoformat = datetime.fromisoformat

            captured_data = [
                {
                    "id": 1,
                    "timestamp": "invalid",
                    "request": {"content": {"system": []}},
                }
            ]

            prompt = strategy.extract_prompt(captured_data)

        assert prompt.timestamp == fake_now

    def test_extract_prompt_raises_for_non_dict_payload(self):
        captured_data = [
            {
                "id": 1,
                "request": {"content": '"just a string"'},
            }
        ]

        strategy = ClaudeCodeStrategy()

        with pytest.raises(ValueError, match="Request content is not valid JSON"):
            strategy.extract_prompt(captured_data)

    def test_extract_prompt_handles_malformed_json_string(self):
        captured_data = [
            {
                "id": 1,
                "timestamp": "2025-01-01T12:00:00Z",
                "request": {"content": "{invalid json"},
            }
        ]

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.system == []
        assert prompt.tools == []

    def test_extract_prompt_defaults_missing_system_and_tools(self):
        captured_data = [
            {
                "id": 1,
                "request": {"content": {"other": "value"}},
            }
        ]

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.system == []
        assert prompt.tools == []

    def test_extract_prompt_populates_metadata_fields(self):
        captured_data = [
            {
                "id": 42,
                "request": {
                    "method": "POST",
                    "url": "https://api.anthropic.com/v1/messages",
                    "content": {"system": []},
                },
            }
        ]

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.metadata["source"] == self.strategy.name
        assert prompt.metadata["capture_id"] == 42
        assert prompt.metadata["request_url"] == "https://api.anthropic.com/v1/messages"
        assert prompt.metadata["request_method"] == "POST"

    def test_extract_prompt_uses_first_capture(self):
        captured_data = [
            {
                "id": 2,
                "request": {
                    "content": {"system": [{"type": "text", "text": "Second"}]}
                },
            },
            {
                "id": 1,
                "request": {"content": {"system": [{"type": "text", "text": "First"}]}},
            },
        ]

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.metadata["capture_id"] == 2
        assert prompt.system[0]["text"] == "Second"

    def test_extract_prompt_requires_data(self):
        with pytest.raises(ValueError, match="No captured data provided"):
            self.strategy.extract_prompt([])
