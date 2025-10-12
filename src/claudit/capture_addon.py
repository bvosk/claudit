import json
import logging
from datetime import datetime

from mitmproxy import http

from claudit.infrastructure.capture import CaptureRepository


class CaptureAddon:
    def __init__(
        self,
        repository: CaptureRepository,
    ):
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
        self._repository = repository

    @property
    def captured_data(self) -> list[dict]:
        return self._repository.all()

    @captured_data.setter
    def captured_data(self, _value) -> None:
        self.request_count = 0
        self._repository.reset()

    def response(self, flow: http.HTTPFlow) -> None:
        """Called when a response is received"""
        if not flow.response:
            self.logger.warning(
                f"Response method called for flow with no response: {flow.request.pretty_url}"
            )
            return

        try:
            next_id = self.request_count + 1
            # Create capture record
            capture_data = {
                "id": next_id,
                "timestamp": datetime.fromtimestamp(
                    flow.response.timestamp_start
                ).isoformat(),
                "request": {
                    "method": flow.request.method,
                    "url": flow.request.pretty_url,
                    "headers": self._mask_sensitive_headers(dict(flow.request.headers)),
                    "content": self._safe_decode_content(flow.request.content),
                    "timestamp": flow.request.timestamp_start,
                },
                "response": {
                    "status_code": flow.response.status_code,
                    "headers": dict(flow.response.headers),
                    "content": self._safe_decode_content(flow.response.content),
                    "timestamp": flow.response.timestamp_start,
                },
                "duration_ms": round(
                    (flow.response.timestamp_start - flow.request.timestamp_start)
                    * 1000,
                    2,
                ),
            }

            stored = self._repository.store(flow, capture_data)
            if stored:
                self.request_count = next_id

            self.logger.debug(
                f"Response headers: {dict(flow.response.headers)}\n"
                f"Response content length: {len(flow.response.content) if flow.response.content else 0} bytes"
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

        self._repository.store(flow, error_data)
        self.logger.error(f"Flow error for {flow.request.pretty_url}: {flow.error}")

    def _mask_sensitive_headers(self, headers: dict) -> dict:
        """Mask sensitive header values for security"""
        sensitive_headers = {
            "x-api-key",
            "authorization",
            "cookie",
            "x-auth-token",
            "x-access-token",
        }
        masked_headers = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in sensitive_headers:
                if isinstance(value, str) and len(value) > 8:
                    # Show first part and mask the rest
                    if key_lower == "x-api-key" and value.startswith("sk-"):
                        masked_headers[key] = f"{value[:8]}****"
                    else:
                        masked_headers[key] = f"{value[:4]}****"
                else:
                    masked_headers[key] = "****"
            else:
                masked_headers[key] = value
        return masked_headers

    def _safe_decode_content(self, content: bytes | None) -> dict | str:
        """Safely decode content with fallback handling, parsing JSON when possible"""
        if not content:
            return ""

        try:
            decoded = content.decode("utf-8")
            # Try to parse as JSON for structured display
            try:
                return json.loads(decoded)
            except json.JSONDecodeError:
                # Not JSON, return as string
                return decoded
        except UnicodeDecodeError:
            try:
                return content.decode("latin1")
            except UnicodeDecodeError:
                return f"<binary data: {len(content)} bytes>"
