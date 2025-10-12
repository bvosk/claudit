from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from claudit.application.capture_service import CaptureService
from claudit.models import Prompt


class _StubStrategy:
    name = "stub"

    def command(self):
        raise NotImplementedError("Should not be called in tests")


class _StubRepository:
    def __init__(self):
        self._captures: List[Dict[str, Any]] = []
        self.reset_calls = 0

    def reset(self) -> None:
        self.reset_calls += 1
        self._captures.clear()

    def all(self) -> List[Dict[str, Any]]:
        return list(self._captures)

    def add(self, capture: Dict[str, Any]) -> None:
        self._captures.append(capture)


class _StubRunner:
    def __init__(self):
        self.addons: List[Any] = []
        self.on_enter = None
        self.entered = False
        self.exited = False

    def add_addon(self, addon: Any) -> None:
        self.addons.append(addon)

    @asynccontextmanager
    async def running(self, ready_timeout: float = 10.0):
        self.entered = True
        if self.on_enter:
            outcome = self.on_enter()
            if inspect.isawaitable(outcome):
                await outcome
        yield object()
        self.exited = True


class _StubCommandRunner:
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.calls = 0

    def run(self) -> Dict[str, Any]:
        self.calls += 1
        return self.payload


class _StubExtractor:
    def __init__(self, prompt: Prompt):
        self.prompt = prompt
        self.called_with: Optional[List[Dict[str, Any]]] = None

    def extract(self, captures: List[Dict[str, Any]]) -> Prompt:
        self.called_with = captures
        return self.prompt


class _StubWriter:
    def __init__(self, path: Path):
        self.path = path
        self.contents: List[str] = []

    def write(self, content: str, *, filename: str | None = None) -> Path:
        self.contents.append(content)
        return self.path


@pytest.mark.asyncio
async def test_run_generates_markdown_when_captures_present():
    repository = _StubRepository()
    runner = _StubRunner()
    command_runner = _StubCommandRunner({"success": True})

    prompt = Prompt(system=["original prompt"])
    scrubbed_prompt = Prompt(system=["scrubbed prompt"])
    extractor = _StubExtractor(prompt=prompt)

    scrub_calls: List[Prompt] = []

    def scrubber(data: Prompt) -> Prompt:
        scrub_calls.append(data)
        return scrubbed_prompt

    markdown_calls: List[Prompt] = []

    def renderer(data: Prompt) -> str:
        markdown_calls.append(data)
        return "# prompt"

    writer = _StubWriter(Path("/tmp/output.md"))
    strategy = _StubStrategy()
    addon = object()

    def populate_capture():
        repository.add({"id": 1})

    runner.on_enter = populate_capture

    service = CaptureService(
        strategy=strategy,
        runner=runner,
        command_runner=command_runner,
        repository=repository,
        capture_addon=addon,
        prompt_extractor=extractor,
        prompt_writer=writer,
        content_scrubber=scrubber,
        prompt_renderer=renderer,
    )

    result = await service.run()

    assert repository.reset_calls == 1
    assert runner.addons == [addon]
    assert command_runner.calls == 1
    assert extractor.called_with == [{"id": 1}]
    assert scrub_calls == [prompt]
    assert markdown_calls == [scrubbed_prompt]
    assert writer.contents == ["# prompt"]
    assert result.markdown_path == writer.path
    assert result.markdown_content == "# prompt"
    assert result.prompt is prompt
    assert result.scrubbed_prompt is scrubbed_prompt
    assert result.agent_result == {"success": True}
    assert result.capture_count == 1


@pytest.mark.asyncio
async def test_run_skips_prompt_when_no_captures():
    repository = _StubRepository()
    runner = _StubRunner()
    command_runner = _StubCommandRunner({"success": False})

    class _SpyExtractor:
        def __init__(self):
            self.called = False

        def extract(self, captures):
            self.called = True
            return Prompt(system=[])

    extractor = _SpyExtractor()

    def scrubber(prompt: Prompt) -> Prompt:
        pytest.fail("scrubber should not be called when there are no captures")

    def renderer(prompt: Prompt) -> str:
        pytest.fail("renderer should not be called when there are no captures")

    class _SpyWriter(_StubWriter):
        def write(self, content: str, *, filename: str | None = None) -> Path:
            pytest.fail("writer should not be invoked when there are no captures")

    writer = _SpyWriter(Path("/tmp/output.md"))
    strategy = _StubStrategy()

    service = CaptureService(
        strategy=strategy,
        runner=runner,
        command_runner=command_runner,
        repository=repository,
        capture_addon=object(),
        prompt_extractor=extractor,
        prompt_writer=writer,
        content_scrubber=scrubber,
        prompt_renderer=renderer,
    )

    result = await service.run()

    assert repository.reset_calls == 1
    assert command_runner.calls == 1
    assert extractor.called is False
    assert result.markdown_path is None
    assert result.markdown_content is None
    assert result.capture_count == 0
