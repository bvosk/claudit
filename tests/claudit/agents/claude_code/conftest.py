from collections.abc import Callable
from typing import Any, Dict

import pytest

from claudit.agents.claude_code import ClaudeCodeStrategy

API_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


@pytest.fixture
def claude_code_strategy() -> ClaudeCodeStrategy:
    return ClaudeCodeStrategy()


@pytest.fixture
def capture_request() -> Callable[..., Dict[str, Any]]:
    def _build(
        *,
        capture_id: int = 1,
        method: str = "POST",
        url: str = API_MESSAGES_URL,
        content: Any | None = None,
        timestamp: str | None = None,
    ) -> Dict[str, Any]:
        request: Dict[str, Any] = {"method": method, "url": url}
        if content is not None:
            request["content"] = content
        capture: Dict[str, Any] = {"id": capture_id, "request": request}
        if timestamp is not None:
            capture["timestamp"] = timestamp
        return capture

    return _build
