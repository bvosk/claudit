from __future__ import annotations

import asyncio
import logging
import socket
from contextlib import asynccontextmanager
from typing import Any, Iterable, Callable

from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster


class MitmproxyRunner:
    """
    Handles mitmproxy lifecycle management: instantiation, readiness polling,
    graceful shutdown, and socket release. Consumers can register addons before
    starting the runner and rely on the async context manager for start/stop.
    """

    def __init__(
        self,
        *,
        proxy_port: int = 8080,
        upstream_base: str = "https://api.anthropic.com",
        listen_host: str = "localhost",
        confdir: str = "/root/.mitmproxy",
        addons: Iterable[Any] | None = None,
        shutdown_timeout: float = 5.0,
        release_delay: float = 0.5,
        open_connection: Callable[..., Any] | None = None,
        sleep: Callable[[float], Any] | None = None,
        logger: logging.Logger | None = None,
        options_cls: Callable[..., Any] = options.Options,
        master_cls: Callable[[Any], DumpMaster] = DumpMaster,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.proxy_port = proxy_port
        self._upstream_base = upstream_base
        self._listen_host = listen_host
        self._confdir = confdir
        self._shutdown_timeout = shutdown_timeout
        self._release_delay = release_delay
        self._open_connection = open_connection or asyncio.open_connection
        self._sleep = sleep or asyncio.sleep
        self._options_cls = options_cls
        self._master_cls = master_cls
        self._addons: list[Any] = list(addons or [])
        self._master: DumpMaster | None = None
        self._task: asyncio.Task | None = None

    def add_addon(self, addon: Any) -> None:
        """Register an addon to be attached when the master is created."""
        self._addons.append(addon)

    @property
    def master(self) -> DumpMaster | None:
        return self._master

    def is_port_available(self, host: str | None = None) -> bool:
        """Detect whether the listener port is free for binding."""
        host = host or self._listen_host
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, self.proxy_port))
                return True
        except OSError:
            return False

    def _build_master(self) -> DumpMaster:
        opts = self._options_cls(
            listen_port=self.proxy_port,
            confdir=self._confdir,
            mode=[f"reverse:{self._upstream_base}"],
        )
        master = self._master_cls(opts)
        for addon in self._addons:
            master.addons.add(addon)
        return master

    async def start(self) -> DumpMaster:
        """Instantiate DumpMaster and launch its event loop task."""
        if self._task and not self._task.done():
            raise RuntimeError("mitmproxy runner already active")

        if not self.is_port_available():
            self.logger.error(
                "Port %d is already in use before mitmproxy startup", self.proxy_port
            )
            raise RuntimeError(f"Port {self.proxy_port} is already in use")

        self.logger.info(
            "Configuring mitmproxy in reverse mode (listen_port=%d)", self.proxy_port
        )
        self._master = self._build_master()
        self._task = asyncio.create_task(self._master.run())
        await self._sleep(0)
        return self._master

    async def wait_until_ready(self, timeout: float = 10.0) -> None:
        """
        Wait until the proxy's TCP listener accepts connections or raise the last
        connection error encountered once timeout expires.
        """
        if not self._task:
            raise RuntimeError("mitmproxy runner has not been started")

        self.logger.debug("Waiting for mitmproxy listener readiness")
        loop = asyncio.get_running_loop()
        start = loop.time()
        attempts = 0
        last_exc: Exception | None = None

        while True:
            try:
                reader, writer = await self._open_connection(
                    self._listen_host, self.proxy_port
                )
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                elapsed = loop.time() - start
                self.logger.info(
                    "mitmproxy listener ready (port=%d) after %.3fs in %d attempt(s)",
                    self.proxy_port,
                    elapsed,
                    attempts + 1,
                )
                return
            except Exception as exc:  # pragma: no cover - loop ensures coverage
                last_exc = exc
                attempts += 1
                if loop.time() - start > timeout:
                    self.logger.error(
                        "mitmproxy not ready after %.1fs (attempts=%d) last_error=%s",
                        timeout,
                        attempts,
                        last_exc,
                    )
                    raise last_exc
                if attempts % 10 == 0:
                    self.logger.debug(
                        "Still waiting for mitmproxy (attempts=%d) last_error=%s",
                        attempts,
                        last_exc,
                    )
                await self._sleep(0.05)

    async def shutdown(self) -> None:
        """Request graceful shutdown and ensure sockets are released."""
        if not self._task:
            return

        if self._master:
            self.logger.debug("Initiating mitmproxy shutdown")
            try:
                self._master.shutdown()
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception("Mitmproxy shutdown raised an exception")

        try:
            await asyncio.wait_for(self._task, timeout=self._shutdown_timeout)
            self.logger.debug("mitmproxy shutdown completed within timeout")
        except asyncio.TimeoutError:
            self.logger.warning(
                "Proxy shutdown timeout after %.1fs; forcing task cancellation",
                self._shutdown_timeout,
            )
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        finally:
            self._master = None
            self._task = None

        await self._sleep(self._release_delay)
        self.logger.info("mitmproxy runner stopped (port=%d)", self.proxy_port)

    @asynccontextmanager
    async def running(self, *, ready_timeout: float = 10.0):
        """
        Async context manager that starts mitmproxy, waits for readiness, and
        guarantees shutdown after use.
        """
        master = await self.start()
        try:
            await self.wait_until_ready(timeout=ready_timeout)
            yield master
        finally:
            await self.shutdown()
