"""Tests for ClaudeContentScrubber"""

from datetime import datetime, timezone
from unittest.mock import patch

from claudit.claude_content_scrubber import ClaudeContentScrubber
from claudit.models import Prompt


class TestClaudeContentScrubber:
    """Test suite for ClaudeContentScrubber class"""

    def test_scrub_text_content_with_date_reference(self):
        """Test scrubbing of date references from text"""
        with patch("claudit.claude_content_scrubber.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2025-09-11"

            text_with_date = "Today's date: 2025-09-11\nOther content here."
            result = ClaudeContentScrubber.scrub(self._from_text(text_with_date))
            prompt_text = self._get_system_text(result)

            assert "Today's date: [date]" in prompt_text
            assert "2025-09-11" not in prompt_text
            assert "Other content here." in prompt_text

    def test_scrub_text_content_empty_string(self):
        """Test scrubbing empty string returns empty string"""
        result = ClaudeContentScrubber.scrub(self._from_text(""))
        prompt_text = self._get_system_text(result)
        assert prompt_text == ""

    def test_scrub_text_content_no_dynamic_content(self):
        """Test scrubbing text with no dynamic content leaves it unchanged"""
        clean_text = "This is clean text with no dynamic content."

        result = ClaudeContentScrubber.scrub(self._from_text(clean_text))
        prompt_text = self._get_system_text(result)

        assert prompt_text == clean_text

    def test_scrub_date_references_specific_date(self):
        """Test date reference scrubbing with specific date"""
        with patch("claudit.claude_content_scrubber.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-12-25"
            result = ClaudeContentScrubber.scrub(self._from_text("Today's date: 2024-12-25 is Christmas!"))
            prompt_text = self._get_system_text(result)

            assert prompt_text == "Today's date: [date] is Christmas!"

    def test_prompt_with_no_metadata(self):
        """Test scrubbing prompt with no metadata"""
        result = ClaudeContentScrubber.scrub(self._from_text("Hello"))

        assert result.metadata == {}

    @staticmethod
    def _from_text(text: str):
        """Create a prompt from text"""
        return Prompt(
            system=[{"type": "text", "text": text}],
            timestamp=datetime.now(timezone.utc),
        )

    @staticmethod
    def _get_system_text(prompt: Prompt):
        """Get the system text from a prompt"""
        return prompt.system[0]["text"]
