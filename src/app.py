#!/usr/bin/env python3

import sys
import signal
import logging
import asyncio

from mitm_capture import MitmproxyCapture


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
