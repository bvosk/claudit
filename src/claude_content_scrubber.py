"""
Claude-specific content scrubber.

This module handles the scrubbing of dynamic or unwanted content from Claude prompts.
"""

import re
import copy
from typing import List, Dict, Any, Optional
from datetime import datetime

from models import Prompt


class ClaudeContentScrubber:
    """Handles scrubbing of dynamic Claude-specific content for snapshot stability."""

    @classmethod
    def scrub_prompt_data(cls, prompt: Prompt) -> Prompt:
        """Scrub all dynamic content from a Prompt object."""
        return Prompt(
            system=[cls._scrub_dict(msg) for msg in prompt.system],
            timestamp=prompt.timestamp,
            tools=[cls._scrub_dict(tool) for tool in prompt.tools],
            metadata=copy.deepcopy(prompt.metadata),
        )

    @classmethod
    def scrub_text_content(cls, text: Optional[str]) -> Optional[str]:
        """Scrub dynamic content from plain text."""
        if not text:
            return text

        # Remove dynamic tool blocks
        scrubbed = re.sub(
            r"^You can use the following tools.*?:.*?(?:\n\n|\Z)",
            "",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )

        # Replace date references
        today = datetime.now().strftime("%Y-%m-%d")
        if today:
            scrubbed = scrubbed.replace(
                f"Today's date: {today}", "Today's date: [date]"
            )

        return scrubbed

    @classmethod
    def scrub_tool_definitions(
        cls, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Scrub dynamic content from tool definitions."""
        return [cls._scrub_dict(tool) for tool in tools]

    @classmethod
    def _scrub_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub text content from dictionary and nested structures."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = cls.scrub_text_content(value)
            elif isinstance(value, dict):
                result[key] = cls._scrub_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    (
                        cls.scrub_text_content(item)
                        if isinstance(item, str)
                        else cls._scrub_dict(item) if isinstance(item, dict) else item
                    )
                    for item in value
                ]
            else:
                result[key] = copy.deepcopy(value)
        return result


__all__ = ["ClaudeContentScrubber"]
