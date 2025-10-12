from pathlib import Path

import pytest

from claudit.models import Prompt
from claudit.prompt_formatter import render_prompt_markdown


# Test data fixtures
@pytest.fixture
def sample_prompt():
    return Prompt(
        system=["You are a helpful assistant."],
        tools=[
            {
                "name": "get_weather",
                "description": "Get weather information",
                "input_schema": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                },
            }
        ],
    )


# Tests for pure functions
class TestRenderPromptMarkdown:

    def test_render_prompt_markdown_success(self, mocker, sample_prompt):
        # Setup mocks
        mock_template_dir = Path("/mock/templates")
        mock_find_template = mocker.patch(
            "claudit.prompt_formatter._find_template_directory"
        )
        mock_find_template.return_value = mock_template_dir

        mock_loader = mocker.patch("claudit.prompt_formatter.FileSystemLoader")
        mock_env = mocker.patch("claudit.prompt_formatter.Environment")

        mock_template = mocker.Mock()
        mock_env.return_value.get_template.return_value = mock_template
        mock_template.render.return_value = '# System Prompt\n\nYou are a helpful assistant.\n\n# Tools\n\n## get_weather\n\n**Description:**\n\n```\nGet weather information\n```\n\n**Schema:**\n```json\n{\n  "type": "object",\n  "properties": {\n    "location": {\n      "type": "string"\n    }\n  }\n}\n```\n'

        # Call function
        result = render_prompt_markdown(sample_prompt)

        # Assertions
        mock_find_template.assert_called_once()
        mock_loader.assert_called_once_with(str(mock_template_dir))
        mock_env.assert_called_once()
        mock_env.return_value.get_template.assert_called_once_with("claudecode.md")
        # Check that template was called with system and tools from prompt
        call_args = mock_template.render.call_args[1]  # Get keyword arguments
        assert "system" in call_args
        assert "tools" in call_args
        assert call_args["system"] == [
            {"type": "text", "text": "You are a helpful assistant."}
        ]
        assert len(call_args["tools"]) == 1
        assert call_args["tools"][0]["name"] == "get_weather"
        assert "# System Prompt" in result
        assert "You are a helpful assistant" in result
        assert "# Tools" in result
        assert "get_weather" in result

    def test_render_prompt_markdown_template_not_found(self, mocker, sample_prompt):
        # Mock Path.exists to return False for all template locations
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match="Template directory not found"):
            render_prompt_markdown(sample_prompt)

    def test_render_prompt_markdown_empty_system(self):
        # Test with empty system messages
        prompt = Prompt(
            system=[],
        )

        # Should not raise exception - template should handle empty lists gracefully
        # This test mainly ensures our function can handle edge cases
        try:
            render_prompt_markdown(prompt)
        except FileNotFoundError:
            # Expected when no template directory - the important thing is
            # we don't crash on empty system messages
            pass

    def test_render_prompt_markdown_empty_tools(self):
        # Test with empty tools list
        prompt = Prompt(
            system=["Hello"],
            tools=[],
        )

        try:
            render_prompt_markdown(prompt)
        except FileNotFoundError:
            # Expected when no template directory - the important thing is
            # we don't crash on empty tools
            pass
