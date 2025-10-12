from __future__ import annotations

from typing import Dict, List


class InMemoryCaptureSink:
    """Simple sink that keeps captures in-memory for tests and diagnostics."""

    def __init__(self):
        self.records: List[Dict] = []

    def persist(self, capture: Dict) -> None:
        self.records.append(capture)

    def reset(self) -> None:
        self.records.clear()
