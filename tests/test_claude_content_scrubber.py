"""Tests for ClaudeContentScrubber"""

from unittest.mock import patch

from claudit.claude_content_scrubber import ClaudeContentScrubber
from claudit.models import Prompt


class TestClaudeContentScrubber:
    """Test suite for ClaudeContentScrubber class"""

    def test_scrub_text_content_with_date_reference(self):
        """Scrubbing replaces dynamic date references in system prompts."""
        with patch("claudit.claude_content_scrubber.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2025-09-11"

            text_with_date = "Today's date: 2025-09-11\nOther content here."
            result = ClaudeContentScrubber.scrub(self._from_text(text_with_date))

        prompt_text = self._get_system_text(result)
        assert "Today's date: [date]" in prompt_text
        assert "2025-09-11" not in prompt_text
        assert "Other content here." in prompt_text

    def test_scrub_text_content_empty_string(self):
        """Scrubbing an empty system prompt leaves it unchanged."""
        result = ClaudeContentScrubber.scrub(self._from_text(""))
        prompt_text = self._get_system_text(result)
        assert prompt_text == ""

    def test_scrub_text_content_no_dynamic_content(self):
        """Scrubbing text without dynamic content does not modify it."""
        clean_text = "This is clean text with no dynamic content."
        result = ClaudeContentScrubber.scrub(self._from_text(clean_text))
        prompt_text = self._get_system_text(result)
        assert prompt_text == clean_text

    def test_scrub_date_references_specific_date(self):
        """Scrubbing handles specific dates consistently."""
        with patch("claudit.claude_content_scrubber.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-12-25"
            result = ClaudeContentScrubber.scrub(
                self._from_text("Today's date: 2024-12-25 is Christmas!")
            )

        prompt_text = self._get_system_text(result)
        assert prompt_text == "Today's date: [date] is Christmas!"

    def test_scrub_tools_nested_text(self):
        """Scrubber recurses into tool structures."""
        prompt = Prompt(
            system=["Static prompt"],
            tools=[
                {
                    "name": "test",
                    "description": "Today's date: 2024-12-25",
                    "nested": ["Keep me", "Today's date: 2024-12-25 too"],
                },
                "plain string tool",
            ],
        )

        with patch("claudit.claude_content_scrubber.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-12-25"
            result = ClaudeContentScrubber.scrub(prompt)

        scrubbed_tool = result.tools[0]
        assert scrubbed_tool["description"] == "Today's date: [date]"
        assert scrubbed_tool["nested"][1] == "Today's date: [date] too"
        assert result.tools[1] == "plain string tool"

    @staticmethod
    def _from_text(text: str) -> Prompt:
        """Create a prompt from text."""
        return Prompt(system=[text])

    @staticmethod
    def _get_system_text(prompt: Prompt) -> str:
        """Get the first system prompt text."""
        return prompt.system[0]
