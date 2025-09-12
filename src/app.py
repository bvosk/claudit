#!/usr/bin/env python3

import sys
import signal
import logging
import os
import asyncio

from mitm_capture import MitmproxyCapture
from prompt_formatter import render_prompt_markdown
from claude_client import ClaudeClient
from claude_content_scrubber import ClaudeContentScrubber
from pathlib import Path


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


async def capture_claude_traffic():
    """Capture Claude's HTTP traffic using the working http_only configuration"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting HTTP traffic capture")
        capture = MitmproxyCapture()
        capture.setup_mitmproxy()
        data = await capture.capture_and_return()
        logger.info(f"Captured {len(data)} requests successfully")
        return data

    except Exception as e:
        logger.error(f"Traffic capture failed: {e}")
        return []


async def async_main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Capture Claude HTTP traffic (suppress mitmproxy output)
    from contextlib import redirect_stdout, redirect_stderr
    import io

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        captured_data = await capture_claude_traffic()

    print(f"Captured {len(captured_data)} requests")

    if captured_data:
        # Create Claude client to extract prompt data
        claude_client = ClaudeClient()

        # Extract prompt from captured HTTP data
        prompt = claude_client.extract_prompt(captured_data)

        # Scrub dynamic content for stable output
        clean_prompt = ClaudeContentScrubber.scrub_prompt_data(prompt)

        # Render markdown using pure function
        markdown_content = render_prompt_markdown(clean_prompt)

        # Handle file I/O in app.py
        prompts_dir = Path("prompts")
        prompts_dir.mkdir(exist_ok=True)
        output_path = prompts_dir / "claudecode.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"Markdown written to {output_path}")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
