#!/usr/bin/env python3

import os
import sys
import signal
import logging
import asyncio
from pathlib import Path
from typing import Optional

import requests
from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster

from capture_addon import CaptureAddon


class MitmproxyCapture:
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.master: Optional[DumpMaster] = None
        self.capture_addon = CaptureAddon(self.capture_file)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self):
        self.target_url = os.getenv("TARGET_URL", "https://httpbin.org/get")
        self.capture_file = os.getenv("CAPTURE_FILE", "/app/captures/requests.txt")
        self.proxy_port = int(os.getenv("PROXY_PORT", "8080"))
        self.curl_headers = os.getenv("CURL_HEADERS", "")
        self.keep_running = os.getenv("KEEP_RUNNING", "false").lower() == "true"

        # Ensure capture directory exists
        Path(self.capture_file).parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Configuration loaded:")
        self.logger.info(f"  Target URL: {self.target_url}")
        self.logger.info(f"  Capture file: {self.capture_file}")
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
            await self.master.run()
        except Exception as e:
            self.logger.error(f"Error running mitmproxy: {e}")
            raise

    def make_request(self):
        """Make HTTP request through the proxy"""
        self.logger.info(f"Making request to {self.target_url}")

        proxies = {
            "http": f"http://localhost:{self.proxy_port}",
            "https": f"http://localhost:{self.proxy_port}",
        }

        headers = {}
        if self.curl_headers:
            for header in self.curl_headers.split(","):
                if ":" in header:
                    key, value = header.split(":", 1)
                    headers[key.strip()] = value.strip()

        try:
            response = requests.get(
                self.target_url,
                proxies=proxies,
                headers=headers,
                verify=False,  # Disable SSL verification for mitmproxy
                timeout=30,
            )
            self.logger.info(
                f"Request completed with status: {
                             response.status_code}"
            )
            return response

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise

    async def run_capture_session(self):
        """Run a complete capture session"""
        try:
            # Start proxy in background
            proxy_task = asyncio.create_task(self.start_proxy())

            # Make the request in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.make_request)

            self.logger.info("Capture session completed")

            # Stop the proxy
            self.master.shutdown()

            # Wait for proxy to finish
            try:
                await asyncio.wait_for(proxy_task, timeout=5)
            except asyncio.TimeoutError:
                self.logger.warning("Proxy shutdown timeout")

        except Exception as e:
            self.logger.error(f"Capture session failed: {e}")
            raise

    def show_results(self):
        """Display captured results"""
        self.logger.info("=== Capture Results ===")
        try:
            with open(self.capture_file, "r") as f:
                content = f.read()
                if content.strip():
                    print(content)
                else:
                    self.logger.warning("No data captured")
        except FileNotFoundError:
            self.logger.error(f"Capture file not found: {self.capture_file}")
        except Exception as e:
            self.logger.error(f"Error reading capture file: {e}")

    async def run(self):
        """Main execution method"""
        self.logger.info("Starting mitmproxy HTTP capture")

        try:
            self.setup_mitmproxy()
            await self.run_capture_session()
            self.show_results()

            if self.keep_running:
                self.logger.info("Keeping container running for inspection...")
                # Keep the container alive
                while True:
                    await asyncio.sleep(60)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Capture failed: {e}")
            sys.exit(1)
        finally:
            if self.master:
                self.master.shutdown()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.getLogger(__name__).info(f"Received signal {signum}")
    sys.exit(0)


async def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    capture = MitmproxyCapture()
    await capture.run()


if __name__ == "__main__":
    asyncio.run(main())
