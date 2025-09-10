import subprocess
import logging
import os
import shutil
from typing import Dict, Any


class ClaudeClient:

    def __init__(self, proxy_port: int = 8080):
        self.proxy_port = proxy_port
        self.proxy_url = f"http://localhost:{proxy_port}"
        self.logger = logging.getLogger(__name__)
        self.last_result: Dict[str, Any] | None = None

    def _build_base_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = f"http://localhost:{self.proxy_port}"
        # This has to be set for CC to make a request. It does not
        # need to be valid since we're interested in the request, not the response.
        env["ANTHROPIC_API_KEY"] = "DUMMY"

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
        cmd = "claude -p hello --model haiku"
        self.logger.info(f"Starting Claude command: {cmd}")

        subprocess_result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=15.0,
            shell=True,
        )

        # Preserve original output contract
        payload = {
            "success": subprocess_result.returncode == 0,
            "returncode": subprocess_result.returncode,
            "stdout": subprocess_result.stdout or "",
            "stderr": subprocess_result.stderr or "",
            "command": cmd,
        }
        self.last_result = payload
        return payload
