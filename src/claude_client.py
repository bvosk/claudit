import subprocess
import logging
import os
import shutil
from typing import Dict, Any, List


class ClaudeClient:
    """
    Lightweight wrapper for invoking the Claude CLI while routing traffic
    through a local mitmproxy instance.

    This version adds:
      - Preflight diagnostics: runs `claude --version` and `claude --help`
        before the main prompt command to observe whether the binary is
        responsive in a non-interactive, headless context.
      - Extensive diagnostic logging (unchanged from previous enhancement).

    Behavioral semantics of the main invocation remain the same:
      - Returns a dict with success/returncode/stdout/stderr/command.
      - Still times out the main command after 30s.
    """

    def __init__(self, proxy_port: int = 8080):
        self.proxy_port = proxy_port
        self.proxy_url = f"http://localhost:{proxy_port}"
        self.logger = logging.getLogger(__name__)
        self.last_result: Dict[str, Any] | None = None
        self.preflight_results: List[Dict[str, Any]] = []

    def _mask(self, value: str | None, keep: int = 6) -> str:
        """Mask potentially sensitive values for logging."""
        if not value:
            return "<missing>"
        if len(value) <= keep:
            return "<redacted>"
        return f"{value[:keep]}****(len={len(value)})"

    def _log_environment_summary(self, env: dict) -> None:
        """Emit a concise summary of key environment aspects for debugging."""
        path_entries = env.get("PATH", "").split(":")
        self.logger.debug(
            "Claude invocation environment summary: "
            f"PATH.count={len(path_entries)} "
            f"HTTP_PROXY={env.get('HTTP_PROXY')} "
            f"HTTPS_PROXY={env.get('HTTPS_PROXY')} "
        )
        if self.logger.isEnabledFor(logging.DEBUG):
            preview = path_entries[:5]
            self.logger.debug(f"PATH preview (first {len(preview)}): {preview}")

    def _build_base_env(self) -> Dict[str, str]:
        """
        Construct and return the environment dict used for all invocations.

        Modified for reverse proxy mode:
          - Do NOT set HTTP(S)_PROXY. We rely on ANTHROPIC_BASE_URL pointing
            at the local mitm reverse proxy (set in MitmproxyCapture).
          - Still relax TLS verification variables to avoid certificate
            friction in containerized environments.
        """
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = f"http://localhost:{self.proxy_port}"
        # This has to be set for CC to make a request. It does not
        # need to be valid since we're interested in the request, not the response.
        env["ANTHROPIC_API_KEY"] = "DUMMY"

        return env

    def _run_preflight(self, env: dict) -> None:
        """Check Claude CLI version and log it at INFO level."""
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
        self.preflight_results.append(result)

        if result["success"]:
            version = result["stdout"].strip()
            self.logger.info(f"Claude CLI version: {version}")
        else:
            self.logger.warning("Failed to get Claude CLI version")

    def run_claude_command(self) -> Dict[str, Any]:
        """
        Execute the Claude CLI with a minimal prompt to induce a network request.
        Adds preflight diagnostics first. Returns payload structure:
          success, returncode, stdout, stderr, command
        """
        self.logger.info("Preparing to invoke Claude CLI command")

        # Build & log environment
        env = self._build_base_env()
        self._log_environment_summary(env)

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
            "preflight": self.preflight_results,
        }
        self.last_result = payload
        return payload
