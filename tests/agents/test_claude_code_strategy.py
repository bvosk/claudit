import json

import pytest

from claudit.agents.claude_code import ClaudeCodeStrategy


class TestClaudeCodeStrategyCommand:
    def test_command_spec_matches_current_cli_invocation(self):
        strategy = ClaudeCodeStrategy()
        spec = strategy.command()

        assert (
            spec.command
            == f"claude -p {ClaudeCodeStrategy.USER_PROMPT} --model haiku"
        )
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


class TestClaudeCodeStrategyPromptExtraction:
    def setup_method(self):
        self.strategy = ClaudeCodeStrategy()

    def test_extract_prompt_parses_dict_payload(self):
        prompt_text = ClaudeCodeStrategy.USER_PROMPT
        captured_data = [
            {
                "id": 1,
                "request": {
                    "method": "POST",
                    "url": "https://api.anthropic.com/v1/messages",
                    "content": {
                        "messages": [{"role": "user", "content": prompt_text}],
                        "system": [
                            {"type": "text", "text": "You are a helpful assistant."}
                        ],
                        "tools": [{"name": "test_tool", "description": "A test tool"}],
                    },
                },
            }
        ]

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.system == ["You are a helpful assistant."]
        assert prompt.tools == [{"name": "test_tool", "description": "A test tool"}]

    def test_extract_prompt_accepts_json_string_payload(self):
        prompt_text = ClaudeCodeStrategy.USER_PROMPT
        content_dict = {
            "messages": [{"role": "user", "content": prompt_text}],
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

        assert prompt.system == ["System prompt"]

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

        with pytest.raises(
            ValueError,
            match="Request content is not valid JSON",
        ):
            self.strategy.extract_prompt(captured_data)

    def test_extract_prompt_converts_non_text_system_entries(self):
        captured_data = [
            {
                "id": 1,
                "request": {
                    "content": {
                        "system": [
                            {"type": "text", "text": "Primary"},
                            {"not": "text"},
                            123,
                        ],
                        "messages": [
                            {
                                "role": "user",
                                "content": ClaudeCodeStrategy.USER_PROMPT,
                            }
                        ],
                    }
                },
            }
        ]

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.system[0] == "Primary"
        assert prompt.system[1].startswith("{")  # serialized fallback
        assert prompt.system[2] == "123"

    def test_extract_prompt_defaults_missing_system_and_tools(self):
        captured_data = [
            {
                "id": 1,
                "request": {
                    "content": {
                        "messages": [
                            {"role": "user", "content": ClaudeCodeStrategy.USER_PROMPT}
                        ]
                    }
                },
            }
        ]

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.system == []
        assert prompt.tools == []

    def test_extract_prompt_matches_request_containing_expected_prompt(self):
        captured_data = [
            {
                "id": 1,
                "request": {
                    "url": "https://api.anthropic.com/v1/messages",
                    "content": {
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"type": "text", "text": "ping"}],
                            }
                        ],
                        "system": [{"type": "text", "text": "Ping system"}],
                    },
                },
            },
            {
                "id": 2,
                "request": {
                    "url": "https://api.anthropic.com/v1/messages",
                    "content": {
                        "system": [{"type": "text", "text": "Primary system prompt"}],
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": ClaudeCodeStrategy.USER_PROMPT,
                                    },
                                    {"type": "text", "text": "extra"},
                                ],
                            }
                        ],
                    },
                },
            },
        ]

        prompt = self.strategy.extract_prompt(captured_data)

        assert prompt.system == ["Primary system prompt"]

    def test_extract_prompt_raises_when_expected_prompt_missing(self):
        prompt_text = ClaudeCodeStrategy.USER_PROMPT
        captured_data = [
            {
                "id": 1,
                "request": {
                    "url": "https://api.anthropic.com/v1/messages",
                    "content": {
                        "system": [{"type": "text", "text": "Fallback system"}],
                        "messages": [{"role": "user", "content": "no target prompt"}],
                    },
                },
            },
            {
                "id": 2,
                "request": {
                    "url": "https://api.anthropic.com/v1/messages?beta=true",
                    "content": {
                        "messages": [{"role": "assistant", "content": "irrelevant"}],
                    },
                },
            },
        ]

        with pytest.raises(
            ValueError,
            match=(
                "Failed to locate captured request containing expected user prompt: "
                f"{prompt_text}"
            ),
        ):
            self.strategy.extract_prompt(captured_data)

    def test_extract_prompt_requires_data(self):
        with pytest.raises(ValueError, match="No captured data provided"):
            self.strategy.extract_prompt([])
