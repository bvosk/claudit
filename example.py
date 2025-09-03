#!/usr/bin/env python3
"""
Simple examples showing how to use the one-liner HTTP capture function.
"""
import asyncio
from src.app import capture_http_traffic


async def basic_example():
    """Basic usage with default settings."""
    print("🔍 Basic HTTP capture example...")
    data = await capture_http_traffic()

    print(f"Captured {len(data)} HTTP transactions:")
    for item in data:
        print(f"  → {item['request']['method']} {item['request']['url']}")
        print(
            f"    Response: {item['response']['status_code']} ({item['duration_ms']}ms)"
        )


async def custom_url_example():
    """Example with custom URL."""
    print("\n🌐 Custom URL example...")
    data = await capture_http_traffic("https://httpbin.org/json")

    for item in data:
        print(f"  → Captured: {item['request']['url']}")
        print(
            f"    Content-Type: {item['response']['headers'].get('Content-Type', 'N/A')}"
        )


async def headers_example():
    """Example with custom headers."""
    print("\n🔑 Custom headers example...")
    data = await capture_http_traffic(
        target_url="https://httpbin.org/headers",
        headers="X-Custom-Header: test-value, User-Agent: MitmProxy-Capture/1.0",
    )

    for item in data:
        print(
            f"  → Request headers included: {list(item['request']['headers'].keys())[:5]}..."
        )


async def main():
    """Run all examples."""
    print("🚀 HTTP Traffic Capture Examples\n")

    try:
        await basic_example()
        await custom_url_example()
        await headers_example()

        print("\n✅ All examples completed successfully!")

    except Exception as e:
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
