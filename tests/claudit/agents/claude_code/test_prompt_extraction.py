import json

import pytest

from claudit.agents.claude_code import ClaudeCodeStrategy


def test_extract_prompt_parses_dict_payload(claude_code_strategy, capture_request):
    prompt_text = ClaudeCodeStrategy.USER_PROMPT
    captured_data = [
        capture_request(
            content={
                "messages": [{"role": "user", "content": prompt_text}],
                "system": [
                    {"type": "text", "text": "You are a helpful assistant."},
                ],
                "tools": [{"name": "test_tool", "description": "A test tool"}],
            },
        )
    ]

    prompt = claude_code_strategy.extract_prompt(captured_data)

    assert prompt.system == ["You are a helpful assistant."]
    assert prompt.tools == [{"name": "test_tool", "description": "A test tool"}]


def test_extract_prompt_accepts_json_string_payload(
    claude_code_strategy, capture_request
):
    prompt_text = ClaudeCodeStrategy.USER_PROMPT
    content_dict = {
        "messages": [{"role": "user", "content": prompt_text}],
        "system": [{"type": "text", "text": "System prompt"}],
        "tools": [],
    }
    captured_data = [
        capture_request(
            timestamp="2025-01-01T12:00:00",
            content=json.dumps(content_dict),
        )
    ]

    prompt = claude_code_strategy.extract_prompt(captured_data)

    assert prompt.system == ["System prompt"]


def test_extract_prompt_raises_for_non_dict_payload(
    claude_code_strategy, capture_request
):
    captured_data = [capture_request(content='"just a string"')]

    with pytest.raises(ValueError, match="Request content is not valid JSON"):
        claude_code_strategy.extract_prompt(captured_data)


def test_extract_prompt_handles_malformed_json_string(
    claude_code_strategy, capture_request
):
    captured_data = [
        capture_request(timestamp="2025-01-01T12:00:00Z", content="{invalid json")
    ]

    with pytest.raises(ValueError, match="Request content is not valid JSON"):
        claude_code_strategy.extract_prompt(captured_data)


def test_extract_prompt_converts_non_text_system_entries(
    claude_code_strategy, capture_request
):
    captured_data = [
        capture_request(
            content={
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
        )
    ]

    prompt = claude_code_strategy.extract_prompt(captured_data)

    assert prompt.system[0] == "Primary"
    assert prompt.system[1].startswith("{")
    assert prompt.system[2] == "123"


def test_extract_prompt_defaults_missing_system_and_tools(
    claude_code_strategy, capture_request
):
    captured_data = [
        capture_request(
            content={
                "messages": [
                    {"role": "user", "content": ClaudeCodeStrategy.USER_PROMPT}
                ]
            }
        )
    ]

    prompt = claude_code_strategy.extract_prompt(captured_data)

    assert prompt.system == []
    assert prompt.tools == []


def test_extract_prompt_matches_request_containing_expected_prompt(
    claude_code_strategy, capture_request
):
    captured_data = [
        capture_request(
            capture_id=1,
            content={
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "ping"}],
                    }
                ],
                "system": [{"type": "text", "text": "Ping system"}],
            },
        ),
        capture_request(
            capture_id=2,
            content={
                "system": [{"type": "text", "text": "Primary system prompt"}],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ClaudeCodeStrategy.USER_PROMPT},
                            {"type": "text", "text": "extra"},
                        ],
                    }
                ],
            },
        ),
    ]

    prompt = claude_code_strategy.extract_prompt(captured_data)

    assert prompt.system == ["Primary system prompt"]


def test_extract_prompt_raises_when_expected_prompt_missing(
    claude_code_strategy, capture_request
):
    prompt_text = ClaudeCodeStrategy.USER_PROMPT
    captured_data = [
        capture_request(
            capture_id=1,
            content={
                "system": [{"type": "text", "text": "Fallback system"}],
                "messages": [{"role": "user", "content": "no target prompt"}],
            },
        ),
        capture_request(
            capture_id=2,
            url="https://api.anthropic.com/v1/messages?beta=true",
            content={
                "messages": [{"role": "assistant", "content": "irrelevant"}],
            },
        ),
    ]

    with pytest.raises(
        ValueError,
        match=(
            "Failed to locate captured request containing expected user prompt: "
            f"{prompt_text}"
        ),
    ):
        claude_code_strategy.extract_prompt(captured_data)


def test_extract_prompt_requires_data(claude_code_strategy):
    with pytest.raises(ValueError, match="No captured data provided"):
        claude_code_strategy.extract_prompt([])
