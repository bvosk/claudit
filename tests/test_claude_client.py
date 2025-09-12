"""Tests for ClaudeClient"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
import json

from claude_client import ClaudeClient
from models import Prompt


class TestClaudeClientExtractPrompt:
    """Test suite for ClaudeClient.extract_prompt method"""

    def test_extract_prompt_basic(self):
        """Test basic prompt extraction from captured data"""
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

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        assert isinstance(result, Prompt)
        assert len(result.system) == 1
        assert result.system[0]["type"] == "text"
        assert result.system[0]["text"] == "You are a helpful assistant."
        assert len(result.tools) == 1
        assert result.tools[0]["name"] == "test_tool"
        assert result.metadata is not None
        assert result.metadata["source"] == "claude_client"
        assert result.metadata["capture_id"] == 1

    def test_extract_prompt_with_string_content(self):
        """Test extraction when request content is a JSON string"""
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

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        assert len(result.system) == 1
        assert result.system[0]["text"] == "System prompt"
        assert result.tools == []

    def test_extract_prompt_empty_data(self):
        """Test extraction fails with empty data"""
        client = ClaudeClient()

        with pytest.raises(ValueError, match="No captured data provided"):
            client.extract_prompt([])

    def test_extract_prompt_malformed_json(self):
        """Test extraction handles malformed JSON gracefully"""
        captured_data = [
            {
                "id": 1,
                "timestamp": "2025-01-01T12:00:00",
                "request": {"content": "invalid json{"},
            }
        ]

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        # Should create empty prompt when JSON is malformed
        assert result.system == []
        assert result.tools == []

    def test_extract_prompt_non_dict_content(self):
        """Test extraction fails with non-dict content after parsing"""
        captured_data = [
            {
                "id": 1,
                "request": {"content": '"just a string"'},  # Valid JSON but not a dict
            }
        ]

        client = ClaudeClient()

        with pytest.raises(ValueError, match="Request content is not valid JSON"):
            client.extract_prompt(captured_data)

    def test_extract_prompt_missing_system_tools(self):
        """Test extraction with missing system/tools fields"""
        captured_data = [
            {
                "id": 1,
                "request": {
                    "content": {"other_field": "value"}  # Missing system and tools
                },
            }
        ]

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        assert result.system == []
        assert result.tools == []

    def test_extract_prompt_invalid_system_type(self):
        """Test extraction when system field is not a list"""
        captured_data = [
            {
                "id": 1,
                "request": {
                    "content": {"system": "not a list", "tools": "also not a list"}
                },
            }
        ]

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        assert result.system == []
        assert result.tools == []

    def test_extract_prompt_timestamp_parsing(self):
        """Test various timestamp format handling"""
        # Test with Z suffix
        captured_data = [
            {
                "id": 1,
                "timestamp": "2025-01-01T12:00:00Z",
                "request": {"content": {"system": [{"type": "text", "text": "test"}]}},
            }
        ]

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        expected_time = datetime.fromisoformat("2025-01-01T12:00:00+00:00")
        assert result.timestamp == expected_time

    def test_extract_prompt_invalid_timestamp(self):
        """Test extraction with invalid timestamp falls back to current time"""
        with patch("claude_client.datetime") as mock_dt:
            mock_now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.fromisoformat = datetime.fromisoformat  # Keep original method

            captured_data = [
                {
                    "id": 1,
                    "timestamp": "invalid-timestamp",
                    "request": {
                        "content": {"system": [{"type": "text", "text": "test"}]}
                    },
                }
            ]

            client = ClaudeClient()
            result = client.extract_prompt(captured_data)

            assert result.timestamp == mock_now

    def test_extract_prompt_missing_timestamp(self):
        """Test extraction with missing timestamp uses current time"""
        with patch("claude_client.datetime") as mock_dt:
            mock_now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now

            captured_data = [
                {
                    "id": 1,
                    # No timestamp field
                    "request": {
                        "content": {"system": [{"type": "text", "text": "test"}]}
                    },
                }
            ]

            client = ClaudeClient()
            result = client.extract_prompt(captured_data)

            assert result.timestamp == mock_now

    def test_extract_prompt_metadata_complete(self):
        """Test extraction creates complete metadata"""
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

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        assert result.metadata is not None
        assert result.metadata["source"] == "claude_client"
        assert result.metadata["capture_id"] == 42
        assert result.metadata["request_url"] == "https://api.anthropic.com/v1/messages"
        assert result.metadata["request_method"] == "POST"

    def test_extract_prompt_multiple_captures_uses_first(self):
        """Test extraction uses first (most recent) capture when multiple provided"""
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

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        # Should use the first item (id=2)
        assert result.system[0]["text"] == "Second capture"
        assert result.metadata is not None
        assert result.metadata["capture_id"] == 2

    def test_extract_prompt_creates_valid_prompt_object(self):
        """Test that extracted Prompt passes validation"""
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

        client = ClaudeClient()
        result = client.extract_prompt(captured_data)

        # Should not raise ValidationError
        result.validate()
        assert isinstance(result, Prompt)
