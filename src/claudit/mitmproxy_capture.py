import asyncio
import logging
from typing import Dict, List

from claudit.agents.base import AgentStrategy
from claudit.agents.claude_code import ClaudeCodeStrategy
from claudit.capture_addon import CaptureAddon
from claudit.infrastructure.agent_command_runner import AgentCommandRunner
from claudit.infrastructure.capture import CaptureRepository
from claudit.infrastructure.capture.sinks.json_file import JsonFileCaptureSink
from claudit.infrastructure.mitmproxy_runner import MitmproxyRunner


class MitmproxyCapture:
    """
    Orchestrates a mitmproxy instance, invokes the agent CLI through it, and
    returns any captured Anthropic API traffic. This version adds enhanced,
    purely observational logging for deeper diagnostics without altering
    functional behavior. Agents provide host/path filtering and CLI hooks via
    strategy injection so capture logic stays decoupled from agent specifics.
    """

    def __init__(
        self,
        proxy_port: int = 8080,
        strategy: AgentStrategy | None = None,
    ):
        self.setup_logging()
        self.proxy_port = proxy_port
        self.strategy: AgentStrategy = strategy or ClaudeCodeStrategy()
        self.master = None
        self.capture_repository = CaptureRepository(
            strategy=self.strategy,
            sink=JsonFileCaptureSink(
                directory="captures", filename=f"{self.strategy.name}.json"
            ),
        )
        self.capture_addon = CaptureAddon(
            repository=self.capture_repository,
        )
        self.command_runner = AgentCommandRunner(
            self.proxy_port, strategy=self.strategy
        )
        self.runner = MitmproxyRunner(proxy_port=self.proxy_port, logger=self.logger)
        self.runner.add_addon(self.capture_addon)
        # Introspection only; not used for control flow
        self.last_agent_result: Dict | None = None

    def setup_logging(self):
        self.logger = logging.getLogger(__name__)

    def _run_agent_and_store(self):
        """
        Invoke the agent CLI via the AgentCommandRunner while proxy is active.
        """
        self.logger.info("Invoking agent CLI through proxy (port=%d)", self.proxy_port)
        result = self.command_runner.run()
        self.last_agent_result = result
        snippet = (result.get("stderr") or result.get("stdout") or "")[:160].replace(
            "\n", " "
        )
        self.logger.info(
            "Agent CLI finished success=%s rc=%s snippet='%s'",
            result.get("success"),
            result.get("returncode"),
            snippet,
        )

    async def capture_and_return(self) -> List[Dict]:
        """
        Run a full capture session:
          1. Start mitmproxy
          2. Wait for listener readiness
          3. Execute agent CLI (in thread executor)
          4. Shutdown mitmproxy
          5. Return captured Anthropic API flows
        """
        self.logger.info("Starting capture session (port=%d)", self.proxy_port)
        try:
            # Clear existing in-memory captures
            self.capture_repository.reset()
            self.logger.debug("Cleared previous captured data buffer")

            try:
                async with self.runner.running() as master:
                    self.master = master
                    # Offload CLI invocation to thread executor to avoid blocking loop
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, self._run_agent_and_store)
            finally:
                self.master = None

            captured_data = self.capture_repository.all()
            self.logger.info("Captured %d qualifying request(s)", len(captured_data))

            self.logger.info(
                "Capture session complete (requests=%d)", len(captured_data)
            )
            return captured_data

        except Exception as e:
            self.logger.error("Capture session failed: %s", e)
            raise
