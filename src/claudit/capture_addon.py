from mitmproxy import http
import logging
import json
import os
from datetime import datetime


class CaptureAddon:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
        self.captured_data = []

        # Create captures directory if it doesn't exist
        os.makedirs("captures", exist_ok=True)

        # Create timestamped filename for this session
        self.capture_file = os.path.join("captures", "claudecode.json")

    def response(self, flow: http.HTTPFlow) -> None:
        """Called when a response is received"""
        # Check if request is to api.anthropic.com
        if not self._is_anthropic_request(flow):
            return

        if not flow.response:
            self.logger.warning(
                f"Response method called for flow with no response: {flow.request.pretty_url}"
            )
            return

        try:
            self.request_count += 1

            # Create capture record
            capture_data = {
                "id": self.request_count,
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

            # Store data in memory
            self.captured_data.append(capture_data)

            # Write to file
            self._write_capture_to_file(capture_data)

            self.logger.debug(
                f"Response headers: {dict(flow.response.headers)}\n"
                f"Response content length: {len(flow.response.content) if flow.response.content else 0} bytes"
            )

        except Exception as e:
            self.logger.error(f"Error capturing response: {e}")

    def error(self, flow: http.HTTPFlow) -> None:
        """Called when a flow encounters an error"""
        # Check if request is to api.anthropic.com
        if not self._is_anthropic_request(flow):
            return

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
        self._write_capture_to_file(error_data)
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

    def _is_anthropic_request(self, flow: http.HTTPFlow) -> bool:
        """Check if the request is to api.anthropic.com"""
        try:
            url = flow.request.url
            return "api.anthropic.com/v1/messages" in url
        except:
            return False

    def _write_capture_to_file(self, capture_data: dict) -> None:
        """Write captured data to timestamped JSON file"""
        try:
            with open(self.capture_file, "w") as f:
                f.write(json.dumps(capture_data, indent=2) + "\n")
        except Exception as e:
            self.logger.error(f"Error writing capture to file: {e}")
