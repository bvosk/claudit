#!/usr/bin/env python3

import sys
import signal
import logging
import asyncio
import socket
from typing import Optional, List, Dict

from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster

from capture_addon import CaptureAddon
from claude_client import ClaudeClient


class MitmproxyCapture:
    def __init__(self, proxy_port=8080):
        self.setup_logging()
        self.proxy_port = proxy_port
        self.master: Optional[DumpMaster] = None
        self.capture_addon = CaptureAddon()
        self.claude_client = ClaudeClient(self.proxy_port)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def is_port_available(self, port: int, host: str = "localhost") -> bool:
        """Check if a port is available for binding"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return True
        except OSError:
            return False

    def setup_mitmproxy(self):
        """Configure and create mitmproxy instance with basic settings"""
        if not self.is_port_available(self.proxy_port):
            raise RuntimeError(f"Port {self.proxy_port} is already in use")

        opts = options.Options(listen_port=self.proxy_port, confdir="/root/.mitmproxy")

        self.master = DumpMaster(opts)
        self.master.addons.add(self.capture_addon)

        self.logger.info(f"mitmproxy configured on port {self.proxy_port}")

    async def start_proxy(self):
        """Start the mitmproxy in background"""
        self.logger.info("Starting mitmproxy...")
        try:
            if not self.master:
                raise RuntimeError(
                    "mitmproxy not configured; call setup_mitmproxy() first"
                )
            await self.master.run()
        except Exception as e:
            self.logger.error(f"Error running mitmproxy: {e}")
            raise

    async def wait_for_proxy_ready(
        self, host: str = "localhost", timeout: float = 10.0
    ):
        """Wait until the mitmproxy TCP listener is accepting connections."""
        loop = asyncio.get_event_loop()
        start = loop.time()
        last_err = None
        while True:
            try:
                reader, writer = await asyncio.open_connection(host, self.proxy_port)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                self.logger.info("mitmproxy is ready")
                return
            except Exception as e:
                last_err = e
                if loop.time() - start > timeout:
                    self.logger.error(
                        f"mitmproxy not ready after {timeout}s: {last_err}"
                    )
                    raise
                await asyncio.sleep(0.05)

    async def capture_and_return(self) -> List[Dict]:
        """Run a complete capture session and return captured data as list of dictionaries"""
        try:
            # Clear any previous captured data
            self.capture_addon.captured_data = []

            # Start proxy in background
            proxy_task = asyncio.create_task(self.start_proxy())
            await self.wait_for_proxy_ready()

            # Run Claude command in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.claude_client.run_claude_command)

            self.logger.info("Capture session completed")

            # Return captured data before cleanup
            captured_data = self.capture_addon.captured_data.copy()

            # Stop the proxy
            if self.master:
                self.master.shutdown()

            # Wait for proxy to finish with longer timeout and force cancellation if needed
            try:
                await asyncio.wait_for(proxy_task, timeout=5)
            except asyncio.TimeoutError:
                self.logger.warning("Proxy shutdown timeout, forcing task cancellation")
                proxy_task.cancel()
                try:
                    await proxy_task
                except asyncio.CancelledError:
                    pass
                if self.master:
                    self.master = None

            # Ensure port is released - wait for system to fully close the socket
            await asyncio.sleep(0.5)

            return captured_data

        except Exception as e:
            self.logger.error(f"Capture session failed: {e}")
            # Ensure cleanup on error
            if self.master:
                try:
                    self.master.shutdown()
                    await asyncio.sleep(1)
                except Exception:
                    pass
            raise


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.getLogger(__name__).info(f"Received signal {signum}")
    sys.exit(0)


async def capture_claude_traffic():
    """Capture Claude's HTTP traffic using the working http_only configuration"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting Claude HTTP traffic capture")
        capture = MitmproxyCapture()
        capture.setup_mitmproxy()
        data = await capture.capture_and_return()
        logger.info(f"Successfully captured {len(data)} requests")
        return data

    except Exception as e:
        logger.error(f"Traffic capture failed: {e}")
        return []


async def async_main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Capture Claude HTTP traffic
    captured_data = await capture_claude_traffic()

    # Print results
    print("\n=== Claude HTTP Traffic Capture ===")
    print(f"Captured {len(captured_data)} requests")
    for item in captured_data:
        print(item)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
