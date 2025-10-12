import json
from pathlib import Path

from claudit.agents.claude_code import ClaudeCodeStrategy
from claudit.domain.prompts.prompt_extractor import PromptExtractor

from claudit.prompt_formatter import render_prompt_markdown


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
    rendered = render_prompt_markdown(scrubbed)

    assert rendered == snapshot(name="claude_prompt_fast")
