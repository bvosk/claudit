"""
Claude-specific content scrubber.

This module handles the scrubbing of dynamic or unwanted content from Claude prompts.
"""

import copy
from typing import Any
from datetime import datetime

from claudit.models import Prompt


class ClaudeContentScrubber:
    """Handles scrubbing of dynamic Claude-specific content for snapshot stability."""

    @classmethod
    def scrub(cls, prompt: Prompt) -> Prompt:
        """Scrub all dynamic content from a Prompt object."""
        return Prompt(
            system=[cls._scrub_text_content(text) for text in prompt.system],
            tools=[cls._scrub_value(tool) for tool in prompt.tools],
        )

    @classmethod
    def _scrub_value(cls, data: Any) -> Any:
        """Scrub text content from arbitrary nested structures."""
        if isinstance(data, str):
            return cls._scrub_text_content(data)
        if isinstance(data, dict):
            return {key: cls._scrub_value(value) for key, value in data.items()}
        if isinstance(data, list):
            return [cls._scrub_value(item) for item in data]
        return copy.deepcopy(data)

    @classmethod
    def _scrub_text_content(cls, text: str) -> str:
        """Scrub dynamic content from plain text."""
        if not text:
            return text

        # Replace date references
        today = datetime.now().strftime("%Y-%m-%d")

        if today:
            return text.replace(f"Today's date: {today}", "Today's date: [date]")

        return text


__all__ = ["ClaudeContentScrubber"]
