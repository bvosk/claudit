from mitmproxy import http
import logging
from datetime import datetime


class CaptureAddon:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
        self.captured_data = []
        self.logger.info("CaptureAddon initialized in memory mode")

    def server_connect(self, conn) -> None:
        """Called when establishing a server connection"""
        try:
            # Try to access connection details safely
            server_info = (
                f"{conn.server_conn.address[0]}:{conn.server_conn.address[1]}"
                if hasattr(conn, "server_conn") and conn.server_conn.address
                else "unknown"
            )
            client_info = (
                f"{conn.client_conn.address[0]}:{conn.client_conn.address[1]}"
                if hasattr(conn, "client_conn") and conn.client_conn.address
                else "unknown"
            )
            self.logger.info(
                f"Attempting to connect to server: {server_info} for client {client_info}"
            )
        except Exception as e:
            self.logger.debug(f"Could not log server connection details: {e}")

    def tls_clienthello(self, data) -> None:
        """Called when TLS ClientHello is received"""
        try:
            # Try to access connection details safely
            server_info = (
                f"{data.context.server.address[0]}:{data.context.server.address[1]}"
                if hasattr(data.context, "server") and data.context.server.address
                else "unknown"
            )
            client_info = (
                f"{data.context.client.address[0]}:{data.context.client.address[1]}"
                if hasattr(data.context, "client") and data.context.client.address
                else "unknown"
            )
            self.logger.info(
                f"TLS handshake initiated for {server_info} with client {client_info}"
            )
        except Exception as e:
            self.logger.debug(f"Could not log TLS connection details: {e}")

    def tls_failed_clienthello(self, data) -> None:
        """Called when TLS ClientHello fails"""
        try:
            # Try to access connection details safely
            server_info = (
                f"{data.context.server.address[0]}:{data.context.server.address[1]}"
                if hasattr(data.context, "server") and data.context.server.address
                else "unknown"
            )
            client_info = (
                f"{data.context.client.address[0]}:{data.context.client.address[1]}"
                if hasattr(data.context, "client") and data.context.client.address
                else "unknown"
            )
            self.logger.error(
                f"TLS handshake failed for {server_info} with client {client_info}"
            )
        except Exception as e:
            self.logger.debug(f"Could not log TLS failure details: {e}")

    def request(self, flow: http.HTTPFlow) -> None:
        """Called when a request is received"""
        self.request_count += 1
        self.logger.info(
            f"Intercepted request #{self.request_count}: {flow.request.method} {flow.request.pretty_url}"
        )
        self.logger.debug(
            f"Request headers: {dict(flow.request.headers)}\n"
            f"Request content length: {len(flow.request.content) if flow.request.content else 0} bytes"
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
