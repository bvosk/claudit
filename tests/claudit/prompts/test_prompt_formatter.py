import pytest

from claudit.prompts import PromptFormatter
from claudit.models import Prompt


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


class TestPromptFormatter:
    def test_render_prompt_success(self, sample_prompt, tmp_path):
        template_path = tmp_path / "prompt.md"
        template_path.write_text(
            "System: {% for prompt in system %}{{ prompt.text }} {% endfor %}\n"
            "Tools: {{ tools | length }}\n"
        )

        formatter = PromptFormatter(template_path)

        result = formatter.render(sample_prompt)

        assert "You are a helpful assistant." in result
        assert "Tools: 1" in result

    def test_init_raises_when_template_missing(self, tmp_path):
        missing_template = tmp_path / "missing.md"

        with pytest.raises(FileNotFoundError):
            PromptFormatter(missing_template)

    def test_render_handles_empty_lists(self, tmp_path):
        template_path = tmp_path / "prompt.md"
        template_path.write_text(
            "System count: {{ system | length }}\n"
            "Tools count: {{ tools | length }}\n"
        )

        formatter = PromptFormatter(template_path)
        prompt = Prompt(system=[], tools=[])

        result = formatter.render(prompt)

        assert "System count: 0" in result
        assert "Tools count: 0" in result
