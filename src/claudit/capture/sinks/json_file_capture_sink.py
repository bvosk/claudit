from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict


class JsonFileCaptureSink:
    """Sink that persists the most recent capture to a JSON file."""

    def __init__(self, directory: str, filename: str):
        self._logger = logging.getLogger(__name__)
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

        path = self._directory / filename
        if not path.suffix:
            path = path.with_suffix(".json")
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def persist(self, capture: Dict) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as handle:
                json.dump(capture, handle, indent=2)
                handle.write("\n")
        except Exception:
            self._logger.exception("Failed to write capture to %s", self._path)

    def reset(self) -> None:
        try:
            if self._path.exists():
                self._path.unlink()
        except Exception:
            self._logger.exception("Failed to reset capture file %s", self._path)
