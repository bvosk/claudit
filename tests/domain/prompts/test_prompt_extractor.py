from typing import Any, Dict, List

import pytest

from claudit.domain.prompts import PromptExtractor
from claudit.models import Prompt


class _FakeStrategy:
    name = "fake"

    def __init__(self, prompt: Prompt):
        self.prompt = prompt
        self.received: List[List[Dict[str, Any]]] = []

    def command(self):
        raise NotImplementedError

    def environment_overrides(self, proxy_port: int):
        return {}

    def version_command(self):
        return None

    def api_hosts(self):
        return ()

    def api_path_prefixes(self):
        return ()

    def scrub_cli_output(self, text: str) -> str:
        return text

    def extract_prompt(self, captured_data: List[Dict[str, Any]]) -> Prompt:
        self.received.append(captured_data)
        return self.prompt


class _ErrorStrategy(_FakeStrategy):
    def extract_prompt(self, captured_data: List[Dict[str, Any]]) -> Prompt:
        raise ValueError("boom")


def test_prompt_extractor_delegates_to_strategy():
    prompt = Prompt(system=[], tools=[])
    strategy = _FakeStrategy(prompt=prompt)
    extractor = PromptExtractor(strategy=strategy)

    captured = [{"id": 1}]
    result = extractor.extract(captured)

    assert result is prompt
    assert strategy.received[0] == captured


def test_prompt_extractor_propagates_strategy_errors():
    prompt = Prompt(system=[], tools=[])
    strategy = _ErrorStrategy(prompt=prompt)
    extractor = PromptExtractor(strategy=strategy)

    with pytest.raises(ValueError, match="boom"):
        extractor.extract([{"id": 1}])
