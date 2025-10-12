from __future__ import annotations

import logging
from typing import Dict, List, Protocol, Sequence

from mitmproxy import http

from claudit.agents.agent_strategy import AgentStrategy


class CaptureSink(Protocol):
    """Minimal interface for persisting captured HTTP data."""

    def persist(self, capture: Dict) -> None:
        """Persist a single capture payload."""
        ...

    def reset(self) -> None:
        """Clear any previously persisted state for a new capture session."""
        ...


class CaptureRepository:
    """
    Persists captured HTTP flows after filtering them through the agent strategy.
    Keeps an in-memory record for callers that need to inspect captured payloads.
    """

    def __init__(self, *, strategy: AgentStrategy, sink: CaptureSink):
        self._logger = logging.getLogger(__name__)
        self._strategy = strategy
        self._sink = sink
        self._captures: List[Dict] = []
        self._api_hosts: Sequence[str] = tuple(
            host.lower() for host in strategy.api_hosts()
        )
        self._api_path_prefixes: Sequence[str] = tuple(strategy.api_path_prefixes())

    def reset(self) -> None:
        """Clear in-memory captures and instruct the sink to reset state."""
        self._captures.clear()
        try:
            self._sink.reset()
        except Exception:
            self._logger.exception("Failed to reset capture sink")

    def all(self) -> List[Dict]:
        """Return a copy of all persisted captures."""
        return list(self._captures)

    def store(self, flow: http.HTTPFlow, capture: Dict) -> bool:
        """
        Persist the given capture if the flow matches the agent strategy filters.

        Returns True when the capture is stored so callers can coordinate ids.
        """
        if not self._should_store(flow):
            return False

        self._captures.append(capture)

        try:
            self._sink.persist(capture)
        except Exception:
            self._logger.exception("Failed to persist capture via sink")

        return True

    def _should_store(self, flow: http.HTTPFlow) -> bool:
        """Determine whether the flow should be persisted for the active agent."""
        try:
            request = flow.request
        except AttributeError:
            return False

        host = (getattr(request, "host", "") or "").lower()
        path = getattr(request, "path", "") or ""

        if self._api_hosts and host not in self._api_hosts:
            return False

        if not self._api_path_prefixes:
            return True

        return any(path.startswith(prefix) for prefix in self._api_path_prefixes)
