import logging
import os
import subprocess
from typing import Any, Dict

from claudit.agents.base import AgentStrategy, CommandSpec
from claudit.agents.claude_code import ClaudeCodeStrategy


class AgentClient:
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
        version_spec = self.strategy.version_command()
        if version_spec is None:
            self.logger.debug("Agent strategy provided no version command; skipping")
            return

        cmd = version_spec.command
        subprocess_result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=version_spec.timeout_seconds or 5.0,
            shell=version_spec.use_shell,
        )

        result = {
            "label": "version",
            "command": cmd,
            "success": subprocess_result.returncode == 0,
            "returncode": subprocess_result.returncode,
            "stdout": subprocess_result.stdout or "",
            "stderr": subprocess_result.stderr or "",
        }

        if result["success"]:
            version = result["stdout"].strip()
            self.logger.info("Agent tool version: %s", version)
        else:
            self.logger.warning("Failed to get agent tool version")

    def run_agent_command(self) -> Dict[str, Any]:
        self.logger.info("Preparing to invoke agent command")

        # Build & log environment
        env = self._build_base_env()

        command_spec: CommandSpec = self.strategy.command()
        self.logger.info(
            "Agent command resolved: %s (shell=%s timeout=%s)",
            command_spec.command,
            command_spec.use_shell,
            command_spec.timeout_seconds,
        )

        # Run preflight diagnostics (non-fatal)
        self._run_preflight(env)

        # Main command (unchanged core behavior)
        cmd = command_spec.command
        self.logger.info("Starting agent command: %s", cmd)

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
