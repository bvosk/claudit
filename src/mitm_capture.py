import socket
import asyncio
import logging
from typing import Optional, List, Dict
from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster
from capture_addon import CaptureAddon
from claude_client import ClaudeClient


class MitmproxyCapture:
    """
    Orchestrates a mitmproxy instance, invokes the Claude CLI through it, and
    returns any captured Anthropic API traffic. This version adds enhanced,
    purely observational logging for deeper diagnostics without altering
    functional behavior.
    """

    def __init__(self, proxy_port: int = 8080):
        self.setup_logging()
        self.proxy_port = proxy_port
        self.master: Optional[DumpMaster] = None
        self.capture_addon = CaptureAddon()
        self.claude_client = ClaudeClient(self.proxy_port)
        # Introspection only; not used for control flow
        self.last_claude_result: Dict | None = None

    # --------------------------------------------------------------------- #
    # Logging setup
    # --------------------------------------------------------------------- #

    def setup_logging(self):
        self.logger = logging.getLogger(__name__)

    # --------------------------------------------------------------------- #
    # Utility
    # --------------------------------------------------------------------- #

    def is_port_available(self, port: int, host: str = "localhost") -> bool:
        """
        Check if a port is available for binding.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return True
        except OSError:
            return False

    # --------------------------------------------------------------------- #
    # mitmproxy lifecycle
    # --------------------------------------------------------------------- #

    def setup_mitmproxy(self):
        """
        Configure and initialize mitmproxy DumpMaster with the capture addon.
        """
        self.logger.info(f"Configuring mitmproxy (listen_port={self.proxy_port})")
        if not self.is_port_available(self.proxy_port):
            self.logger.error(
                "Port %d is already in use before mitmproxy startup", self.proxy_port
            )
            raise RuntimeError(f"Port {self.proxy_port} is already in use")

        opts = options.Options(listen_port=self.proxy_port, confdir="/root/.mitmproxy")
        self.master = DumpMaster(opts)
        self.master.addons.add(self.capture_addon)
        self.logger.debug("mitmproxy DumpMaster created; capture addon registered")

    async def start_proxy(self):
        """
        Run mitmproxy event loop until shutdown is requested.
        """
        try:
            if not self.master:
                raise RuntimeError(
                    "mitmproxy not configured; call setup_mitmproxy() first"
                )
            self.logger.info("Starting mitmproxy event loop")
            await self.master.run()
            self.logger.debug("mitmproxy event loop exited normally")
        except Exception as e:
            self.logger.error(f"Error running mitmproxy: {e}")
            raise

    async def wait_for_proxy_ready(
        self, host: str = "localhost", timeout: float = 10.0
    ):
        """
        Poll until the TCP listener accepts connections or timeout elapses.
        """
        self.logger.debug("Waiting for mitmproxy listener readiness")
        loop = asyncio.get_event_loop()
        start = loop.time()
        attempts = 0
        last_err = None
        while True:
            try:
                reader, writer = await asyncio.open_connection(host, self.proxy_port)
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
            except Exception as e:
                last_err = e
                attempts += 1
                if loop.time() - start > timeout:
                    self.logger.error(
                        "mitmproxy not ready after %.1fs (attempts=%d) last_error=%s",
                        timeout,
                        attempts,
                        last_err,
                    )
                    raise
                if attempts % 10 == 0:
                    self.logger.debug(
                        "Still waiting for mitmproxy (attempts=%d) last_error=%s",
                        attempts,
                        last_err,
                    )
                await asyncio.sleep(0.05)

    # --------------------------------------------------------------------- #
    # Claude invocation
    # --------------------------------------------------------------------- #

    def _run_claude_and_store(self):
        """
        Invoke the Claude CLI via the ClaudeClient while proxy is active.
        """
        self.logger.info("Invoking Claude CLI through proxy (port=%d)", self.proxy_port)
        result = self.claude_client.run_claude_command()
        self.last_claude_result = result
        snippet = (result.get("stderr") or result.get("stdout") or "")[:160].replace(
            "\n", " "
        )
        self.logger.info(
            "Claude CLI finished success=%s rc=%s snippet='%s'",
            result.get("success"),
            result.get("returncode"),
            snippet,
        )

    # --------------------------------------------------------------------- #
    # Public capture orchestration
    # --------------------------------------------------------------------- #

    async def capture_and_return(self) -> List[Dict]:
        """
        Run a full capture session:
          1. Start mitmproxy
          2. Wait for listener readiness
          3. Execute Claude CLI (in thread executor)
          4. Shutdown mitmproxy
          5. Return captured Anthropic API flows
        """
        self.logger.info("Starting capture session (port=%d)", self.proxy_port)
        try:
            # Clear existing in-memory captures
            self.capture_addon.captured_data = []
            self.logger.debug("Cleared previous captured data buffer")

            # Start mitmproxy concurrently
            proxy_task = asyncio.create_task(self.start_proxy())
            await self.wait_for_proxy_ready()

            # Offload CLI invocation to thread executor to avoid blocking loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_claude_and_store)

            # Snapshot captured flows
            captured_data = self.capture_addon.captured_data.copy()
            self.logger.info("Captured %d qualifying request(s)", len(captured_data))

            # Begin graceful shutdown
            if self.master:
                self.logger.debug("Initiating mitmproxy shutdown")
                self.master.shutdown()

            try:
                await asyncio.wait_for(proxy_task, timeout=5)
                self.logger.debug("mitmproxy shutdown completed within timeout")
            except asyncio.TimeoutError:
                self.logger.warning(
                    "Proxy shutdown timeout after 5s; forcing task cancellation"
                )
                proxy_task.cancel()
                try:
                    await proxy_task
                except asyncio.CancelledError:
                    pass
                if self.master:
                    self.master = None

            # Allow OS to release socket reliably
            await asyncio.sleep(0.5)
            self.logger.info(
                "Capture session complete (requests=%d)", len(captured_data)
            )
            return captured_data

        except Exception as e:
            self.logger.error("Capture session failed: %s", e)
            if self.master:
                try:
                    self.logger.debug(
                        "Attempting emergency mitmproxy shutdown after failure"
                    )
                    self.master.shutdown()
                    await asyncio.sleep(1)
                except Exception:
                    pass
            raise
