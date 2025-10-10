import logging
from typing import Dict

import requests


class HttpClient:
    """Handles HTTP request operations through proxy"""

    def __init__(self, proxy_port: int):
        self.proxy_port = proxy_port
        self.logger = logging.getLogger(__name__)

    def make_request(
        self, target_url: str, headers_string: str = "", timeout: int = 30
    ) -> requests.Response:
        """Make HTTP request through the proxy"""
        proxies = {
            "http": f"http://localhost:{self.proxy_port}",
            "https": f"http://localhost:{self.proxy_port}",
        }

        headers = self._parse_headers(headers_string)

        try:
            response = requests.get(
                target_url,
                proxies=proxies,
                headers=headers,
                verify=False,
                timeout=timeout,
            )
            return response

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise

    def _parse_headers(self, headers_string: str) -> Dict[str, str]:
        """Parse comma-separated header string into dictionary"""
        headers = {}
        if headers_string:
            for header in headers_string.split(","):
                if ":" in header:
                    key, value = header.split(":", 1)
                    headers[key.strip()] = value.strip()
        return headers
