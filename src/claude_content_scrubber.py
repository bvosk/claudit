"""
Claude-specific content scrubber.

This module handles the scrubbing of dynamic or unwanted content from Claude prompts.
It's designed to be the single source of truth for all Claude content cleaning logic.
"""

import re
import copy
from typing import List, Dict, Any
from datetime import datetime

from models import Prompt


class ClaudeContentScrubber:
    """
    Handles scrubbing of dynamic Claude-specific content for snapshot stability.

    This class is responsible for removing or normalizing content that varies
    between runs and would cause unstable test snapshots or inconsistent output.
    """

    # Pattern to match dynamic tool capability sections
    TOOLS_BLOCK_PATTERN = re.compile(
        r"^You can use the following tools.*?:.*?(?:\n\n|\Z)", re.MULTILINE | re.DOTALL
    )

    # Pattern to match today's date references
    DATE_PATTERN_PREFIX = "Today's date: "

    @classmethod
    def scrub_prompt_data(cls, prompt: Prompt) -> Prompt:
        """
        Scrub all dynamic content from a Prompt object.

        Returns a new Prompt with cleaned system messages and tools.
        Does not modify the original prompt.

        Args:
            prompt: The Prompt object to scrub

        Returns:
            A new Prompt object with scrubbed content
        """
        # Deep copy to avoid modifying original
        scrubbed_system = [cls._scrub_system_message(msg) for msg in prompt.system]
        scrubbed_tools = [cls._scrub_tool_definition(tool) for tool in prompt.tools]

        return Prompt(
            system=scrubbed_system,
            timestamp=prompt.timestamp,
            tools=scrubbed_tools,
            metadata=copy.deepcopy(prompt.metadata),
        )

    @classmethod
    def scrub_text_content(cls, text: str) -> str:
        """
        Scrub dynamic content from plain text.

        Removes:
        - Dynamic tool capability sections
        - Today's date references (replaced with placeholder)

        Args:
            text: The text content to scrub

        Returns:
            Scrubbed text content
        """
        if not text:
            return text

        # Remove dynamic tool blocks
        scrubbed = cls.TOOLS_BLOCK_PATTERN.sub("", text)

        # Replace date references
        scrubbed = cls._scrub_date_references(scrubbed)

        return scrubbed

    @classmethod
    def scrub_tool_definitions(
        cls, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Scrub dynamic content from tool definitions.

        Args:
            tools: List of tool definition dictionaries

        Returns:
            List of scrubbed tool definitions
        """
        return [cls._scrub_tool_definition(tool) for tool in tools]

    @classmethod
    def _scrub_system_message(cls, message: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub dynamic content from a single system message."""
        scrubbed_msg = copy.deepcopy(message)

        if "text" in scrubbed_msg and isinstance(scrubbed_msg["text"], str):
            scrubbed_msg["text"] = cls.scrub_text_content(scrubbed_msg["text"])

        return scrubbed_msg

    @classmethod
    def _scrub_tool_definition(cls, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub dynamic content from a single tool definition."""
        scrubbed_tool = copy.deepcopy(tool)

        # Scrub text fields in tool definition
        for key, value in scrubbed_tool.items():
            if isinstance(value, str):
                scrubbed_tool[key] = cls.scrub_text_content(value)
            elif isinstance(value, dict):
                scrubbed_tool[key] = cls._scrub_dict_recursively(value)

        return scrubbed_tool

    @classmethod
    def _scrub_dict_recursively(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively scrub text content in dictionary structures."""
        scrubbed = {}

        for key, value in data.items():
            if isinstance(value, str):
                scrubbed[key] = cls.scrub_text_content(value)
            elif isinstance(value, dict):
                scrubbed[key] = cls._scrub_dict_recursively(value)
            elif isinstance(value, list):
                scrubbed[key] = [
                    (
                        cls.scrub_text_content(item)
                        if isinstance(item, str)
                        else (
                            cls._scrub_dict_recursively(item)
                            if isinstance(item, dict)
                            else item
                        )
                    )
                    for item in value
                ]
            else:
                scrubbed[key] = value

        return scrubbed

    @classmethod
    def _scrub_date_references(cls, text: str) -> str:
        """Replace today's date with a placeholder for stability."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today:
            text = re.sub(
                re.escape(f"{cls.DATE_PATTERN_PREFIX}{today}"),
                f"{cls.DATE_PATTERN_PREFIX}[date]",
                text,
            )
        return text


__all__ = ["ClaudeContentScrubber"]
