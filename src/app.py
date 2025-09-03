#!/usr/bin/env python3

import sys
import signal
import logging
import asyncio
from typing import Optional, List, Dict

from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster

from capture_addon import CaptureAddon
from http_client import HttpClient


class MitmproxyCapture:
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.master: Optional[DumpMaster] = None
        self.capture_addon = CaptureAddon()
        self.http_client = HttpClient(self.proxy_port)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self):
        self.target_url = "https://httpbin.org/get"
        self.proxy_port = 8080
        self.curl_headers = ""

        self.logger.info("Configuration loaded:")
        self.logger.info(f"  Target URL: {self.target_url}")
        self.logger.info(f"  Proxy port: {self.proxy_port}")

    def setup_mitmproxy(self):
        """Configure and create mitmproxy instance"""
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

    def make_request(self):
        """Make HTTP request through the proxy"""
        return self.http_client.make_request(
            target_url=self.target_url, headers_string=self.curl_headers
        )

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

            # Make the request in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.make_request)

            self.logger.info("Capture session completed")

            # Stop the proxy
            if self.master:
                self.master.shutdown()

            # Wait for proxy to finish
            try:
                await asyncio.wait_for(proxy_task, timeout=5)
            except asyncio.TimeoutError:
                self.logger.warning("Proxy shutdown timeout")

            # Return captured data
            return self.capture_addon.captured_data.copy()

        except Exception as e:
            self.logger.error(f"Capture session failed: {e}")
            raise


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.getLogger(__name__).info(f"Received signal {signum}")
    sys.exit(0)


async def capture_http_traffic(target_url=None, proxy_port=8080, headers=""):
    """One-liner function to capture HTTP traffic and return structured data.

    Args:
        target_url: URL to capture (default: https://httpbin.org/get)
        proxy_port: Proxy port to use (default: 8080)
        headers: Headers to include in request (default: "")

    Returns:
        List of captured HTTP request/response dictionaries
    """
    capture = MitmproxyCapture()
    if target_url:
        capture.target_url = target_url
    if proxy_port != 8080:
        capture.proxy_port = proxy_port
        capture.http_client = HttpClient(proxy_port)
    if headers:
        capture.curl_headers = headers

    capture.setup_mitmproxy()
    return await capture.capture_and_return()


async def async_main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Example usage of the one-liner function
    data = await capture_http_traffic()

    # Print captured data
    for item in data:
        print(item)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
