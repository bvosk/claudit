from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List, Sequence, cast

from mitmproxy import http

from claudit.agents.agent_strategy import AgentStrategy, CommandSpec
from claudit.capture import CaptureRepository
from claudit.capture.sinks import JsonFileCaptureSink


class _StubStrategy(AgentStrategy):
    def __init__(
        self,
        *,
        hosts: Sequence[str] = (),
        prefixes: Sequence[str] = (),
    ):
        self.name = "stub"
        self._hosts = hosts
        self._prefixes = prefixes

    def command(self) -> CommandSpec:
        return CommandSpec(command="stub")

    def environment_overrides(self, proxy_port: int) -> Dict[str, str]:
        return {}

    def version_command(self) -> CommandSpec | None:
        return None

    def api_hosts(self) -> Sequence[str]:
        return self._hosts

    def api_path_prefixes(self) -> Sequence[str]:
        return self._prefixes

    def extract_prompt(self, captured_data: List[Dict[str, Any]]):
        raise NotImplementedError


def _flow(host: str, path: str) -> http.HTTPFlow:
    request = SimpleNamespace(host=host, path=path)
    return cast(http.HTTPFlow, SimpleNamespace(request=request))


def test_store_persists_matching_flow(tmp_path):
    strategy = _StubStrategy(
        hosts=("api.anthropic.com",),
        prefixes=("/v1/messages",),
    )
    sink = JsonFileCaptureSink(directory=str(tmp_path), filename="capture.json")
    repository = CaptureRepository(strategy=strategy, sink=sink)

    flow = _flow("api.anthropic.com", "/v1/messages")
    capture = {"id": 1}

    stored = repository.store(flow, capture)

    assert stored is True
    assert repository.all() == [capture]
    assert json.loads(sink.path.read_text(encoding="utf-8")) == capture


def test_store_skips_non_matching_host(tmp_path):
    strategy = _StubStrategy(
        hosts=("api.anthropic.com",),
        prefixes=("/v1/messages",),
    )
    sink = JsonFileCaptureSink(directory=str(tmp_path), filename="capture.json")
    repository = CaptureRepository(strategy=strategy, sink=sink)

    flow = _flow("other.example.com", "/v1/messages")

    stored = repository.store(flow, {"id": 1})

    assert stored is False
    assert repository.all() == []
    assert not sink.path.exists()


def test_store_skips_non_matching_path(tmp_path):
    strategy = _StubStrategy(
        hosts=("api.anthropic.com",),
        prefixes=("/v1/messages",),
    )
    sink = JsonFileCaptureSink(directory=str(tmp_path), filename="capture.json")
    repository = CaptureRepository(strategy=strategy, sink=sink)

    flow = _flow("api.anthropic.com", "/v1/other")

    stored = repository.store(flow, {"id": 1})

    assert stored is False
    assert repository.all() == []
    assert not sink.path.exists()


def test_reset_clears_in_memory_and_sink(tmp_path):
    strategy = _StubStrategy(
        hosts=("api.anthropic.com",),
        prefixes=("/v1/messages",),
    )
    sink = JsonFileCaptureSink(directory=str(tmp_path), filename="capture.json")
    repository = CaptureRepository(strategy=strategy, sink=sink)

    flow = _flow("api.anthropic.com", "/v1/messages")
    repository.store(flow, {"id": 1})

    repository.reset()

    assert repository.all() == []
    assert not sink.path.exists()
