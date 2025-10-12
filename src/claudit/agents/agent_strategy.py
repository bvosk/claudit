from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, Sequence

from claudit.models import Prompt


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """
    Declarative command descriptor so agents can control invocation without
    the caller needing to know implementation details (shell vs argv, timeouts).
    """

    command: str
    use_shell: bool = True
    timeout_seconds: float | None = None


class AgentStrategy(Protocol):
    """
    Contract for agent-specific behaviour spanning CLI invocation,
    network capture filtering, prompt extraction, and CLI output scrubbing.
    """

    name: str

    def command(self) -> CommandSpec:
        """Return the primary CLI command to execute for this agent."""
        ...

    def environment_overrides(self, proxy_port: int) -> Dict[str, str]:
        """
        Provide environment overrides that should be merged on top of the base
        environment prior to executing the agent command.
        """
        ...

    def version_command(self) -> CommandSpec | None:
        """
        Optional CLI command used to report tool version information before
        running the main agent workflow. Returning None skips the preflight.
        """
        ...

    def api_hosts(self) -> Sequence[str]:
        """Hosts whose traffic should be captured for this agent."""
        ...

    def api_path_prefixes(self) -> Sequence[str]:
        """Path prefixes that further scope qualifying traffic."""
        ...

    def scrub_cli_output(self, text: str) -> str:
        """Apply any CLI stdout/stderr scrubbing required for snapshot stability."""
        ...

    def extract_prompt(self, captured_data: List[Dict[str, Any]]) -> Prompt:
        """Convert captured HTTP payloads into a domain Prompt object."""
        ...

    def scrub_prompt(self, prompt: Prompt) -> Prompt:
        """
        Apply any agent-specific prompt scrubbing (e.g. redacting dynamic or
        non-deterministic content) prior to rendering or snapshotting.
        Implementations may return the prompt unchanged if no scrubbing is needed.
        """
        ...
