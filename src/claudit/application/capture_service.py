from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from claudit.agents.agent_strategy import AgentStrategy
from claudit.capture_addon import CaptureAddon
from claudit.domain.prompts import PromptExtractor, PromptWriter
from claudit.infrastructure.agent_command_runner import AgentCommandRunner
from claudit.infrastructure.capture import CaptureRepository
from claudit.infrastructure.capture.sinks.json_file import JsonFileCaptureSink
from claudit.infrastructure.mitmproxy_runner import MitmproxyRunner
from claudit.models import Prompt


PromptScrubber = Callable[[Prompt], Prompt]
PromptRenderer = Callable[[Prompt], str]


@dataclass(slots=True)
class CaptureWorkflowResult:
    captures: List[Dict]
    agent_result: Optional[Dict]
    prompt: Optional[Prompt]
    scrubbed_prompt: Optional[Prompt]
    markdown_content: Optional[str]
    markdown_path: Optional[Path]

    @property
    def capture_count(self) -> int:
        return len(self.captures)


class CaptureService:
    """
    Coordinates the end-to-end capture workflow for an agent strategy, including
    mitmproxy orchestration, CLI execution, prompt extraction, scrubbing, and
    Markdown emission through the provided writer.
    """

    def __init__(
        self,
        *,
        strategy: AgentStrategy,
        runner: MitmproxyRunner,
        command_runner: AgentCommandRunner,
        repository: CaptureRepository,
        capture_addon: CaptureAddon,
        prompt_extractor: PromptExtractor,
        prompt_writer: PromptWriter,
        content_scrubber: PromptScrubber,
        prompt_renderer: PromptRenderer,
        logger: Optional[logging.Logger] = None,
    ):
        self.strategy = strategy
        self._runner = runner
        self._command_runner = command_runner
        self._repository = repository
        self._capture_addon = capture_addon
        self._prompt_extractor = prompt_extractor
        self._prompt_writer = prompt_writer
        self._content_scrubber = content_scrubber
        self._prompt_renderer = prompt_renderer
        self._logger = logger or logging.getLogger(__name__)
        self._runner.add_addon(self._capture_addon)
        self._last_agent_result: Optional[Dict] = None

    @property
    def last_agent_result(self) -> Optional[Dict]:
        return self._last_agent_result

    async def run(self) -> CaptureWorkflowResult:
        """Execute the capture workflow and return aggregate results."""
        self._repository.reset()
        self._logger.info(
            "Starting capture workflow for strategy '%s'", self.strategy.name
        )

        loop = asyncio.get_running_loop()

        try:
            async with self._runner.running():
                self._logger.debug("Proxy running; invoking agent command")
                self._last_agent_result = await loop.run_in_executor(
                    None, self._command_runner.run
                )
        finally:
            self._logger.debug("Capture workflow proxy context exited")

        captures = self._repository.all()
        self._logger.info("Captured %d request(s)", len(captures))

        prompt: Prompt | None = None
        scrubbed_prompt: Prompt | None = None
        markdown_content: str | None = None
        markdown_path: Path | None = None

        if captures:
            prompt = self._prompt_extractor.extract(captures)
            scrubbed_prompt = self.strategy.scrub_prompt(prompt)
            markdown_content = self._prompt_renderer(scrubbed_prompt)
            markdown_path = self._prompt_writer.write(markdown_content)
            self._logger.info("Prompt written to %s", markdown_path)
        else:
            self._logger.info("No qualifying captures; skipping prompt generation")

        return CaptureWorkflowResult(
            captures=captures,
            agent_result=self._last_agent_result,
            prompt=prompt,
            scrubbed_prompt=scrubbed_prompt,
            markdown_content=markdown_content,
            markdown_path=markdown_path,
        )

    @classmethod
    def build(
        cls,
        *,
        strategy: AgentStrategy,
        proxy_port: int = 8080,
        captures_directory: str = "captures",
        prompts_directory: Path | str | None = None,
        content_scrubber: PromptScrubber,
        prompt_renderer: PromptRenderer,
        logger: Optional[logging.Logger] = None,
    ) -> "CaptureService":
        """
        Convenience constructor wiring default infrastructure for the supplied strategy.
        """
        log = logger or logging.getLogger(__name__)
        repository = CaptureRepository(
            strategy=strategy,
            sink=JsonFileCaptureSink(
                directory=captures_directory, filename=f"{strategy.name}.json"
            ),
        )
        capture_addon = CaptureAddon(repository=repository)
        runner = MitmproxyRunner(proxy_port=proxy_port, logger=log)
        command_runner = AgentCommandRunner(proxy_port, strategy=strategy)
        prompt_extractor = PromptExtractor(strategy=strategy)
        prompts_dir = Path(prompts_directory) if prompts_directory else Path("prompts")
        prompt_writer = PromptWriter(prompts_dir, filename=f"{strategy.name}.md")

        return cls(
            strategy=strategy,
            runner=runner,
            command_runner=command_runner,
            repository=repository,
            capture_addon=capture_addon,
            prompt_extractor=prompt_extractor,
            prompt_writer=prompt_writer,
            content_scrubber=content_scrubber,
            prompt_renderer=prompt_renderer,
            logger=log,
        )
