from mitmproxy import http
import json
import logging
from datetime import datetime
from pathlib import Path


class CaptureAddon:
    def __init__(self, output_file: str):
        self.output_file = Path(output_file)
        self.logger = logging.getLogger(__name__)
        self.request_count = 0

        # Ensure output directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # Clear previous capture data
        with open(self.output_file, "w") as f:
            f.write("")

        self.logger.info(f"CaptureAddon initialized, writing to: {self.output_file}")

    def request(self, flow: http.HTTPFlow) -> None:
        """Called when a request is received"""
        self.request_count += 1
        self.logger.info(
            f"Intercepted request #{self.request_count}: {flow.request.method} {flow.request.pretty_url}"
        )

    def response(self, flow: http.HTTPFlow) -> None:
        """Called when a response is received"""
        try:
            # Extract request information
            request_info = {
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "headers": dict(flow.request.headers),
                "content": self._safe_decode_content(flow.request.content),
                "timestamp": flow.request.timestamp_start,
            }

            # Extract response information
            response_info = {
                "status_code": flow.response.status_code,
                "headers": dict(flow.response.headers),
                "content": self._safe_decode_content(flow.response.content),
                "timestamp": flow.response.timestamp_start,
            }

            # Create capture record
            capture_data = {
                "id": self.request_count,
                "timestamp": datetime.fromtimestamp(
                    flow.response.timestamp_start
                ).isoformat(),
                "request": request_info,
                "response": response_info,
                "duration_ms": round(
                    (flow.response.timestamp_start - flow.request.timestamp_start)
                    * 1000,
                    2,
                ),
            }

            # Write to file as JSON lines format
            self._write_capture_data(capture_data)

            self.logger.info(
                f"Captured response: {flow.response.status_code} for {flow.request.pretty_url}"
            )

        except Exception as e:
            self.logger.error(f"Error capturing response: {e}")

    def error(self, flow: http.HTTPFlow) -> None:
        """Called when a flow encounters an error"""
        error_data = {
            "id": self.request_count,
            "timestamp": datetime.now().isoformat(),
            "error": True,
            "request": {
                "method": flow.request.method,
                "url": flow.request.pretty_url,
            },
            "error_message": str(flow.error) if flow.error else "Unknown error",
        }

        self._write_capture_data(error_data)
        self.logger.error(f"Flow error for {flow.request.pretty_url}: {flow.error}")

    def _safe_decode_content(self, content: bytes) -> str:
        """Safely decode content with fallback handling"""
        if not content:
            return ""

        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return content.decode("latin1")
            except UnicodeDecodeError:
                return f"<binary data: {len(content)} bytes>"

    def _write_capture_data(self, data: dict) -> None:
        """Write capture data to output file"""
        try:
            with open(self.output_file, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write capture data: {e}")


# For backwards compatibility when used as standalone addon
def response(flow: http.HTTPFlow) -> None:
    """Standalone function for direct mitmproxy usage"""
    addon = CaptureAddon("/tmp/capture.jsonl")
    addon.response(flow)
