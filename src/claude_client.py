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

    # -----------------------
    # Internal helper methods
    # -----------------------

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
            f"ANTHROPIC_API_KEY(masked)={self._mask(env.get('ANTHROPIC_API_KEY'))}"
        )
        if self.logger.isEnabledFor(logging.DEBUG):
            preview = path_entries[:5]
            self.logger.debug(f"PATH preview (first {len(preview)}): {preview}")

    def _build_base_env(self) -> Dict[str, str]:
        """
        Construct and return the environment dict used for all invocations.
        (No functional change relative to the main command's previous logic.)
        """
        env = os.environ.copy()

        # Clear and then set proxy-related variables (explicit baseline)
        env["HTTP_PROXY"] = ""
        env["HTTPS_PROXY"] = ""
        env["CURL_CA_BUNDLE"] = ""
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        env["PYTHONHTTPSVERIFY"] = "0"
        env["NO_PROXY"] = ""
        env["SOCKS_PROXY"] = ""

        # Set proxy (HTTP-only interception still applied to HTTPS via CONNECT)
        env["HTTP_PROXY"] = self.proxy_url
        env["HTTPS_PROXY"] = self.proxy_url  ## COMMENTING THIS OUT STOPS THE HANGING

        # Ensure an API key is present so the CLI *tries* to do something
        if "ANTHROPIC_API_KEY" not in env:
            env["ANTHROPIC_API_KEY"] = "DUMMY_KEY"

        return env

    def _run_subprocess(
        self,
        cmd: str,
        env: dict,
        timeout: float,
        label: str,
        log_preview: int = 300,
        allow_error: bool = True,
    ) -> Dict[str, Any]:
        """
        Generic subprocess runner for diagnostics and main command.
        Returns a standardized payload; does NOT raise (except unexpected exceptions).
        """
        self.logger.info(f"[{label}] Starting command: {cmd} (timeout={timeout}s)")
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True,  # Preserving original behavior
            )
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            rc = result.returncode

            if rc == 0:
                self.logger.info(
                    f"[{label}] Completed rc=0 stdout_len={len(stdout)} stderr_len={len(stderr)}"
                )
            else:
                level = logging.WARNING if allow_error else logging.ERROR
                self.logger.log(
                    level,
                    f"[{label}] Non-zero rc={rc} stdout_len={len(stdout)} stderr_len={len(stderr)}",
                )
                if stderr:
                    self.logger.debug(
                        f"[{label}] stderr preview: {stderr[:log_preview].rstrip()}"
                    )

            return {
                "label": label,
                "command": cmd,
                "success": rc == 0,
                "returncode": rc,
                "stdout": stdout,
                "stderr": stderr,
            }

        except subprocess.TimeoutExpired as e:
            partial_stdout = (
                e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            )
            partial_stderr = (
                e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            )
            self.logger.error(
                f"[{label}] Timed out after {timeout:.1f}s: {cmd} "
                f"partial_stdout_len={len(partial_stdout)} partial_stderr_len={len(partial_stderr)}"
            )
            return {
                "label": label,
                "command": cmd,
                "success": False,
                "returncode": -1,
                "stdout": partial_stdout,
                "stderr": "Command timed out",
            }
        except FileNotFoundError:
            self.logger.error(f"[{label}] Command not found: {cmd.split()[0]}")
            return {
                "label": label,
                "command": cmd,
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Command not found",
            }
        except Exception as e:
            self.logger.error(f"[{label}] Unexpected error: {e}")
            return {
                "label": label,
                "command": cmd,
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
            }

    # -----------------------
    # Preflight diagnostics
    # -----------------------

    def _run_preflight(self, env: dict) -> None:
        """
        Execute quick diagnostic commands to determine if the CLI responds
        in a headless environment before issuing the main prompt command.
        These results are stored in self.preflight_results and logged.
        """
        preflights = [
            ("claude --version", 5.0, "preflight:version"),
            ("claude --help", 5.0, "preflight:help"),
        ]

        for cmd, timeout, label in preflights:
            result = self._run_subprocess(
                cmd=cmd,
                env=env,
                timeout=timeout,
                label=label,
                allow_error=True,
                log_preview=400,
            )
            self.preflight_results.append(result)

            # Summarize outcomes at INFO level
            summary = (
                f"[{label}] success={result['success']} rc={result['returncode']} "
                f"stdout_len={len(result['stdout'])} stderr_len={len(result['stderr'])}"
            )
            self.logger.info(summary)

            # If stdout is short, log inline for convenience
            if result["stdout"] and len(result["stdout"]) < 200:
                self.logger.debug(
                    f"[{label}] stdout inline: {result['stdout'].strip()}"
                )

    # -----------------------
    # Public API
    # -----------------------

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

        result = self._run_subprocess(
            cmd=cmd,
            env=env,
            timeout=15.0,
            label="main",
            allow_error=True,
            log_preview=300,
        )

        # Preserve original output contract
        payload = {
            "success": result["success"],
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "command": result["command"],
            "preflight": self.preflight_results,
        }
        self.last_result = payload
        return payload
