"""Tests for ClaudeContentScrubber"""

# removed unused pytest import
from datetime import datetime, timezone
from unittest.mock import patch

from claude_content_scrubber import ClaudeContentScrubber
from models import Prompt


class TestClaudeContentScrubber:
    """Test suite for ClaudeContentScrubber class"""

    def test_scrub_text_content_with_tools_block(self):
        """Test scrubbing of dynamic tools block from text"""
        text_with_tools = """Some content before.

You can use the following tools without requiring user approval: Bash(uv run pytest:*)

Some content after."""

        result = ClaudeContentScrubber.scrub_text_content(text_with_tools)

        assert "You can use the following tools" not in result
        assert "Some content before." in result
        assert "Some content after." in result

    def test_scrub_text_content_with_date_reference(self):
        """Test scrubbing of date references from text"""
        with patch("claude_content_scrubber.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2025-09-11"

            text_with_date = "Today's date: 2025-09-11\nOther content here."
            result = ClaudeContentScrubber.scrub_text_content(text_with_date)

            assert "Today's date: [date]" in result
            assert "2025-09-11" not in result
            assert "Other content here." in result

    def test_scrub_text_content_empty_string(self):
        """Test scrubbing empty string returns empty string"""
        result = ClaudeContentScrubber.scrub_text_content("")
        assert result == ""

    def test_scrub_text_content_none_input(self):
        """Test scrubbing None input returns None"""
        result = ClaudeContentScrubber.scrub_text_content(None)
        assert result is None

    def test_scrub_text_content_no_dynamic_content(self):
        """Test scrubbing text with no dynamic content leaves it unchanged"""
        clean_text = "This is clean text with no dynamic content."
        result = ClaudeContentScrubber.scrub_text_content(clean_text)
        assert result == clean_text

    def test_scrub_prompt_data_basic(self):
        """Test scrubbing basic Prompt object"""
        system_msgs = [
            {"type": "text", "text": "You are a helpful assistant."},
            {"type": "text", "text": "You can use the following tools: Bash(test)"},
        ]
        tools = [{"name": "test_tool", "description": "A test tool"}]
        timestamp = datetime.now(timezone.utc)

        prompt = Prompt(
            system=system_msgs,
            timestamp=timestamp,
            tools=tools,
            metadata={"source": "test"},
        )

        result = ClaudeContentScrubber.scrub_prompt_data(prompt)

        # Should be a new object
        assert result is not prompt

        # Basic fields should be preserved
        assert result.timestamp == timestamp
        assert result.metadata == {"source": "test"}

        # System messages should be scrubbed
        assert len(result.system) == 2
        assert result.system[0]["text"] == "You are a helpful assistant."
        assert "You can use the following tools" not in result.system[1]["text"]

    def test_scrub_prompt_data_preserves_original(self):
        """Test that scrubbing doesn't modify the original Prompt"""
        original_text = "You can use the following tools: Bash(test)"
        system_msgs = [{"type": "text", "text": original_text}]
        timestamp = datetime.now(timezone.utc)

        original_prompt = Prompt(system=system_msgs, timestamp=timestamp)

        ClaudeContentScrubber.scrub_prompt_data(original_prompt)

        # Original should be unchanged
        assert original_prompt.system[0]["text"] == original_text

    def test_scrub_tool_definitions(self):
        """Test scrubbing tool definitions"""
        tools = [
            {
                "name": "test_tool",
                "description": "You can use the following tools: Bash(test)",
                "input_schema": {
                    "type": "object",
                    "description": "You can use the following tools: Another(test)",
                },
            }
        ]

        result = ClaudeContentScrubber.scrub_tool_definitions(tools)

        assert len(result) == 1
        assert result[0]["name"] == "test_tool"  # Name unchanged
        assert "You can use the following tools" not in result[0]["description"]
        assert (
            "You can use the following tools"
            not in result[0]["input_schema"]["description"]
        )

    def test_scrub_system_message_with_complex_content(self):
        """Test scrubbing system message with nested content"""
        message = {
            "type": "text",
            "text": "System prompt\n\nYou can use the following tools without approval: Bash(test)\n\nMore content",
        }

        result = ClaudeContentScrubber._scrub_dict(message)

        assert result["type"] == "text"
        assert "System prompt" in result["text"]
        assert "More content" in result["text"]
        assert "You can use the following tools" not in result["text"]

    def test_scrub_dict_recursively(self):
        """Test recursive scrubbing of dictionary structures"""
        test_dict = {
            "level1": "You can use the following tools: Test(1)",
            "nested": {
                "level2": "You can use the following tools: Test(2)",
                "deep_nested": {"level3": "You can use the following tools: Test(3)"},
            },
            "list_field": [
                "You can use the following tools: Test(4)",
                {"inner": "You can use the following tools: Test(5)"},
            ],
        }

        result = ClaudeContentScrubber._scrub_dict(test_dict)

        # All dynamic content should be removed
        assert "You can use the following tools" not in str(result)

        # Structure should be preserved
        assert "level1" in result
        assert "nested" in result
        assert "level2" in result["nested"]
        assert "deep_nested" in result["nested"]
        assert "level3" in result["nested"]["deep_nested"]
        assert len(result["list_field"]) == 2

    def test_scrub_date_references_specific_date(self):
        """Test date reference scrubbing with specific date"""
        with patch("claude_content_scrubber.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-12-25"

            text = "Today's date: 2024-12-25 is Christmas!"
            result = ClaudeContentScrubber.scrub_text_content(text)

            assert result == "Today's date: [date] is Christmas!"

    def test_multiple_tools_blocks_scrubbed(self):
        """Test that multiple tools blocks are all scrubbed"""
        text = """First section.

You can use the following tools without approval: Tool1(arg)

Middle section.

You can use the following tools: Tool2(arg), Tool3(arg)

Final section."""

        result = ClaudeContentScrubber.scrub_text_content(text)

        assert "You can use the following tools" not in result
        assert "First section." in result
        assert "Middle section." in result
        assert "Final section." in result

    def test_tools_block_at_end_of_text(self):
        """Test tools block at the very end of text (no trailing newlines)"""
        text = "Some content.\n\nYou can use the following tools: EndTool(test)"

        result = ClaudeContentScrubber.scrub_text_content(text)

        assert "You can use the following tools" not in result
        assert "Some content." in result

    def test_prompt_with_empty_tools_list(self):
        """Test scrubbing prompt with empty tools list"""
        prompt = Prompt(
            system=[{"type": "text", "text": "Hello world"}],
            timestamp=datetime.now(timezone.utc),
            tools=[],
        )

        result = ClaudeContentScrubber.scrub_prompt_data(prompt)

        assert result.tools == []
        assert len(result.system) == 1

    def test_prompt_with_no_metadata(self):
        """Test scrubbing prompt with no metadata"""
        prompt = Prompt(
            system=[{"type": "text", "text": "Hello"}],
            timestamp=datetime.now(timezone.utc),
        )

        result = ClaudeContentScrubber.scrub_prompt_data(prompt)

        assert result.metadata == {}
