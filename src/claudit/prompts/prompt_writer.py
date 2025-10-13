from __future__ import annotations

from pathlib import Path


class PromptWriter:
    """
    Handles filesystem persistence for rendered prompt artefacts. Centralising
    this logic keeps rendering pure and makes it easier to substitute sinks.
    """

    def __init__(self, output_dir: Path | str, *, filename: str | None = None):
        self._output_dir = Path(output_dir)
        self._default_filename = filename

    def write(self, content: str, *, filename: str | None = None) -> Path:
        target_name = filename or self._default_filename
        if not target_name:
            raise ValueError("PromptWriter requires a filename to write output")

        self._output_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._output_dir / target_name
        target_path.write_text(content, encoding="utf-8")
        return target_path
