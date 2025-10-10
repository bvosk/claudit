"""Tests for ClaudeContentScrubber"""

# removed unused pytest import
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
            result = ClaudeContentScrubber.scrub_text_content(text_with_date)

            assert "Today's date: [date]" in result
            assert "2025-09-11" not in result
            assert "Other content here." in result

    def test_scrub_text_content_empty_string(self):
        """Test scrubbing empty string returns empty string"""
        result = ClaudeContentScrubber.scrub_text_content("")
        assert result == ""

    def test_scrub_text_content_no_dynamic_content(self):
        """Test scrubbing text with no dynamic content leaves it unchanged"""
        clean_text = "This is clean text with no dynamic content."
        result = ClaudeContentScrubber.scrub_text_content(clean_text)
        assert result == clean_text

    def test_scrub_date_references_specific_date(self):
        """Test date reference scrubbing with specific date"""
        with patch("claudit.claude_content_scrubber.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2024-12-25"

            text = "Today's date: 2024-12-25 is Christmas!"
            result = ClaudeContentScrubber.scrub_text_content(text)

            assert result == "Today's date: [date] is Christmas!"

    def test_prompt_with_no_metadata(self):
        """Test scrubbing prompt with no metadata"""
        prompt = Prompt(
            system=[{"type": "text", "text": "Hello"}],
            timestamp=datetime.now(timezone.utc),
        )

        result = ClaudeContentScrubber.scrub_prompt_data(prompt)

        assert result.metadata == {}
