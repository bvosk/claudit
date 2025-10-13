import json
from pathlib import Path

from claudit.agents.claude_code import ClaudeCodeStrategy
from claudit.application.prompt_formatter import (
    DEFAULT_TEMPLATE_PATH,
    PromptFormatter,
)
from claudit.domain.prompts.prompt_extractor import PromptExtractor


def test_tests_claude_code_fast_integration(snapshot):
    """Fast integration snapshot: extract -> scrub -> render Claude prompt.

    Uses a real captured request payload to assert end-to-end correctness of
    prompt extraction, content scrubbing, and markdown rendering without
    invoking the slower docker-based workflow.
    """
    strategy = ClaudeCodeStrategy()
    extractor = PromptExtractor(strategy)

    fixture_path = Path(__file__).parent / "fixtures" / "claudecode_real_capture.json"
    raw_record = json.loads(fixture_path.read_text())

    prompt = extractor.extract([raw_record])
    scrubbed = strategy.scrub_prompt(prompt)
    formatter = PromptFormatter(DEFAULT_TEMPLATE_PATH)
    rendered = formatter.render(scrubbed)

    assert rendered == snapshot(name="claude_prompt_fast")
