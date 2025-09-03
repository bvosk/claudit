from mitmproxy import http
import logging
from datetime import datetime


class CaptureAddon:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
        self.captured_data = []
        self.logger.info("CaptureAddon initialized in memory mode")

    def request(self, flow: http.HTTPFlow) -> None:
        """Called when a request is received"""
        self.request_count += 1
        self.logger.info(
            f"Intercepted request #{self.request_count}: {flow.request.method} {flow.request.pretty_url}"
        )

    def response(self, flow: http.HTTPFlow) -> None:
        """Called when a response is received"""
        if not flow.response:
            self.logger.warning(
                f"Response method called for flow with no response: {flow.request.pretty_url}"
            )
            return

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

            # Store data in memory
            self.captured_data.append(capture_data)

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

        self.captured_data.append(error_data)
        self.logger.error(f"Flow error for {flow.request.pretty_url}: {flow.error}")

    def _safe_decode_content(self, content: bytes | None) -> str:
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
