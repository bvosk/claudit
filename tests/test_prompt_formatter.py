import pytest

from pathlib import Path
from datetime import datetime, timezone

from models import CapturedRequest
from prompt_formatter import render_prompt_markdown


# Test data fixtures
@pytest.fixture
def sample_captured_request():
    return CapturedRequest(
        id=1,
        timestamp=datetime.now(timezone.utc),
        method="POST",
        url="https://api.anthropic.com/v1/messages",
        request_headers={
            "Authorization": "Bearer sk-ant-...",
            "Content-Type": "application/json",
        },
        request_body={
            "system": [{"type": "text", "text": "You are a helpful assistant."}],
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get weather information",
                    "input_schema": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                }
            ],
        },
        response_status=200,
        response_headers={"Content-Type": "application/json"},
        response_body={"content": [{"text": "Hello!"}]},
    )


# Tests for pure functions
class TestRenderPromptMarkdown:

    def test_render_prompt_markdown_success(self, mocker, sample_captured_request):
        # Setup mocks
        mock_template_dir = Path("/mock/templates")
        mock_find_template = mocker.patch("prompt_formatter._find_template_directory")
        mock_find_template.return_value = mock_template_dir

        mock_loader = mocker.patch("prompt_formatter.FileSystemLoader")
        mock_env = mocker.patch("prompt_formatter.Environment")

        mock_template = mocker.Mock()
        mock_env.return_value.get_template.return_value = mock_template
        mock_template.render.return_value = '# System Prompt\n\nYou are a helpful assistant.\n\n# Tools\n\n## get_weather\n\n**Description:**\n\n```\nGet weather information\n```\n\n**Schema:**\n```json\n{\n  "type": "object",\n  "properties": {\n    "location": {\n      "type": "string"\n    }\n  }\n}\n```\n'

        # Call function
        result = render_prompt_markdown(sample_captured_request)

        # Assertions
        mock_find_template.assert_called_once()
        mock_loader.assert_called_once_with(str(mock_template_dir))
        mock_env.assert_called_once()
        mock_env.return_value.get_template.assert_called_once_with("claudecode.md")
        mock_template.render.assert_called_once_with(
            system=[{"type": "text", "text": "You are a helpful assistant."}],
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
        assert "# System Prompt" in result
        assert "You are a helpful assistant" in result
        assert "# Tools" in result
        assert "get_weather" in result

    def test_render_prompt_markdown_template_not_found(
        self, mocker, sample_captured_request
    ):
        # Mock Path.exists to return False for all template locations
        mock_exists = mocker.patch("pathlib.Path.exists")
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match="Template directory not found"):
            render_prompt_markdown(sample_captured_request)

    def test_render_prompt_markdown_invalid_request_body(self, sample_captured_request):
        # Test with invalid JSON string in request body
        sample_captured_request.request_body = "invalid json"

        with pytest.raises(ValueError, match="Failed to parse request content as JSON"):
            render_prompt_markdown(sample_captured_request)

    def test_render_prompt_markdown_non_dict_request_body(
        self, sample_captured_request
    ):
        # Test with non-parseable body type
        sample_captured_request.request_body = 123

        with pytest.raises(ValueError, match="Request body is not parseable JSON"):
            render_prompt_markdown(sample_captured_request)
