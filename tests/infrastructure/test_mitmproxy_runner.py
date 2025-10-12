from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from claudit.infrastructure.mitmproxy_runner import MitmproxyRunner


class _StubWriter:
    def __init__(self, events: list[str]):
        self._events = events

    def close(self) -> None:
        self._events.append("close")

    async def wait_closed(self) -> None:
        self._events.append("wait_closed")


class _StubMaster:
    def __init__(self):
        self.addons = SimpleNamespace(add=lambda addon: None)
        self._stop = asyncio.Event()

    async def run(self) -> None:
        await self._stop.wait()

    def shutdown(self) -> None:
        self._stop.set()


class _StuckMaster:
    def __init__(self):
        self.addons = SimpleNamespace(add=lambda addon: None)

    async def run(self) -> None:
        await asyncio.Future()

    def shutdown(self) -> None:
        pass


async def _fake_sleep(_: float) -> None:
    return None


def _options_factory(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


@pytest.mark.asyncio
async def test_running_context_starts_and_shuts_down_cleanly():
    events: list[str] = []

    async def fake_open_connection(host: str, port: int):
        events.append(f"{host}:{port}")
        return object(), _StubWriter(events)

    runner = MitmproxyRunner(
        proxy_port=9090,
        open_connection=fake_open_connection,
        sleep=_fake_sleep,
        options_cls=_options_factory,
        master_cls=lambda opts: _StubMaster(),
    )
    addon = object()
    runner.add_addon(addon)

    async with runner.running():
        assert runner.master is not None
        assert events == ["localhost:9090", "close", "wait_closed"]

    assert runner.master is None


@pytest.mark.asyncio
async def test_wait_until_ready_raises_last_exception():
    attempts = 0

    async def failing_connection(host: str, port: int):
        nonlocal attempts
        attempts += 1
        raise ConnectionRefusedError(f"{host}:{port}")

    runner = MitmproxyRunner(
        proxy_port=1234,
        open_connection=failing_connection,
        sleep=_fake_sleep,
        options_cls=_options_factory,
        master_cls=lambda opts: _StubMaster(),
    )

    await runner.start()
    with pytest.raises(ConnectionRefusedError):
        await runner.wait_until_ready(timeout=0.05)

    await runner.shutdown()
    assert attempts > 0


@pytest.mark.asyncio
async def test_shutdown_cancels_when_master_never_stops():
    runner = MitmproxyRunner(
        proxy_port=12000,
        sleep=_fake_sleep,
        options_cls=_options_factory,
        master_cls=lambda opts: _StuckMaster(),
        shutdown_timeout=0.01,
    )

    await runner.start()
    await runner.shutdown()
    assert runner.master is None
