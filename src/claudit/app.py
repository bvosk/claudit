#!/usr/bin/env python3

import logging
import signal
import os
import asyncio
import io
import sys
from contextlib import redirect_stdout, redirect_stderr

from claudit.agents.claude_code import ClaudeCodeStrategy
from claudit.application.capture_service import CaptureService
from claudit.claude_content_scrubber import ClaudeContentScrubber
from claudit.prompt_formatter import render_prompt_markdown


# Configure centralized logging
def setup_logging():
    """Set up centralized logging configuration"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.WARNING)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Only add handler if not already configured
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Set specific loggers to reduce noise
    logging.getLogger("mitmproxy").setLevel(logging.CRITICAL)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Filter out mitmproxy console output
    class MitmproxyFilter(logging.Filter):
        def filter(self, record):
            return not (hasattr(record, "name") and "mitmproxy" in record.name)

    root_logger.addFilter(MitmproxyFilter())


setup_logging()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.getLogger(__name__).warning(f"Received signal {signum}, shutting down")
    sys.exit(0)


async def async_main():
    strategy = ClaudeCodeStrategy()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        workflow_service = CaptureService.build(
            strategy=strategy,
            content_scrubber=ClaudeContentScrubber.scrub_prompt_data,
            prompt_renderer=render_prompt_markdown,
        )
        result = await workflow_service.run()

    captured_data = result.captures

    print(f"Captured {len(captured_data)} requests")

    if result.markdown_path:
        print(f"Markdown written to {result.markdown_path}")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
