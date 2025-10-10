import subprocess
import logging
import os
import shutil
from typing import Dict, Any, List

from claudit.agents.base import AgentStrategy, CommandSpec
from claudit.agents.claude_code import ClaudeCodeStrategy
from claudit.models import Prompt


class ClaudeClient:

    def __init__(
        self,
        proxy_port: int = 8080,
        strategy: AgentStrategy | None = None,
    ):
        self.proxy_port = proxy_port
        self.proxy_url = f"http://localhost:{proxy_port}"
        self.logger = logging.getLogger(__name__)
        self.last_result: Dict[str, Any] | None = None
        self.strategy: AgentStrategy = strategy or ClaudeCodeStrategy()

    def _build_base_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env.update(self.strategy.environment_overrides(self.proxy_port))
        return env

    def _run_preflight(self, env: dict) -> None:

        subprocess_result = subprocess.run(
            "claude -v",
            env=env,
            capture_output=True,
            text=True,
            timeout=5.0,
            shell=True,
        )

        result = {
            "label": "version",
            "command": "claude -v",
            "success": subprocess_result.returncode == 0,
            "returncode": subprocess_result.returncode,
            "stdout": subprocess_result.stdout or "",
            "stderr": subprocess_result.stderr or "",
        }

        if result["success"]:
            version = result["stdout"].strip()
            self.logger.info(f"Claude CLI version: {version}")
        else:
            self.logger.warning("Failed to get Claude CLI version")

    def run_claude_command(self) -> Dict[str, Any]:
        self.logger.info("Preparing to invoke Claude CLI command")

        # Build & log environment
        env = self._build_base_env()

        # Resolve executable path for transparency
        claude_path = shutil.which("claude")
        self.logger.info(
            f"Resolved 'claude' executable path: {claude_path or '<not found>'}"
        )

        # Run preflight diagnostics (non-fatal)
        self._run_preflight(env)

        # Main command (unchanged core behavior)
        command_spec: CommandSpec = self.strategy.command()
        cmd = command_spec.command
        self.logger.info(f"Starting Claude command: {cmd}")

        subprocess_result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=command_spec.timeout_seconds or 15.0,
            shell=command_spec.use_shell,
        )

        # Preserve original output contract
        raw_stdout = subprocess_result.stdout or ""
        raw_stderr = subprocess_result.stderr or ""
        cleaned_stdout = self.strategy.scrub_cli_output(raw_stdout)
        cleaned_stderr = self.strategy.scrub_cli_output(raw_stderr)
        payload = {
            "success": subprocess_result.returncode == 0,
            "returncode": subprocess_result.returncode,
            "stdout": cleaned_stdout,
            "stderr": cleaned_stderr,
            "command": cmd,
        }
        self.last_result = payload
        return payload

    def extract_prompt(self, captured_data: List[Dict[str, Any]]) -> Prompt:
        """Extract a Prompt via the active agent strategy."""
        return self.strategy.extract_prompt(captured_data)
