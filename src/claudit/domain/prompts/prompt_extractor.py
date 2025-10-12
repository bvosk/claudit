from __future__ import annotations

from typing import Any, Dict, List

from claudit.agents.base import AgentStrategy
from claudit.models import Prompt


class PromptExtractor:
    """
    Thin strategy-aware façade for turning captured HTTP traffic into a Prompt.
    Keeping the orchestration separate from the agent client simplifies testing
    and aligns with the layered refactor plan.
    """

    def __init__(self, strategy: AgentStrategy):
        self._strategy = strategy

    def extract(self, captured_data: List[Dict[str, Any]]) -> Prompt:
        return self._strategy.extract_prompt(captured_data)
