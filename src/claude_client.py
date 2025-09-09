import subprocess
import logging
import os
import shutil
from typing import Dict, Any


class ClaudeClient:
    """
    Lightweight wrapper for invoking the Claude CLI while routing traffic
    through a local mitmproxy instance. This version adds extensive diagnostic
    logging without changing behavioral semantics or return structure.
    """

    def __init__(self, proxy_port: int = 8080):
        self.proxy_port = proxy_port
        self.proxy_url = f"http://localhost:{proxy_port}"
        self.logger = logging.getLogger(__name__)
        # For post-execution inspection (not used for flow control)
        self.last_result: Dict[str, Any] | None = None

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
            # Log first few PATH entries for clarity
            preview = path_entries[:5]
            self.logger.debug(f"PATH preview (first {len(preview)}): {preview}")

    # -----------------------
    # Public API
    # -----------------------

    def run_claude_command(self) -> Dict[str, Any]:
        """
        Execute the Claude CLI with a minimal prompt to induce a network request.
        Returns a dictionary with:
          success: bool
          returncode: int
          stdout: str
          stderr: str
          command: str
        """
        self.logger.info("Preparing to invoke Claude CLI command")

        # Prepare environment (preserving semantics of original implementation)
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
        env["HTTPS_PROXY"] = self.proxy_url

        # Ensure the CLI attempts a network call (dummy key unchanged)
        if "ANTHROPIC_API_KEY" not in env:
            env["ANTHROPIC_API_KEY"] = "DUMMY_KEY"

        # Log summarized environment diagnostics
        self._log_environment_summary(env)

        # Resolve executable path for transparency
        claude_path = shutil.which("claude")
        self.logger.info(
            f"Resolved 'claude' executable path: {claude_path or '<not found>'}"
        )

        cmd = "claude -p hello --model haiku"
        self.logger.info(f"Starting Claude command: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True,  # Preserved from original for identical behavior
            )

            stdout_len = len(result.stdout or "")
            stderr_len = len(result.stderr or "")
            if result.returncode == 0:
                self.logger.info(
                    "Claude command completed successfully "
                    f"rc=0 stdout_len={stdout_len} stderr_len={stderr_len}"
                )
            else:
                self.logger.warning(
                    "Claude command finished with non-zero return code "
                    f"rc={result.returncode} stdout_len={stdout_len} stderr_len={stderr_len}"
                )
                # Provide a trimmed preview of stderr for diagnostics
                if result.stderr:
                    self.logger.debug(
                        "Claude stderr (first 300 chars): "
                        f"{result.stderr[:300].rstrip()}"
                    )

            payload = {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": cmd,
            }
            self.last_result = payload
            return payload

        except subprocess.TimeoutExpired as e:
            # Maintain original semantics while enriching log detail
            partial_stdout = (
                e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            )
            partial_stderr = (
                e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            )
            self.logger.error(
                "Command timed out after %.1fs: %s partial_stdout_len=%d partial_stderr_len=%d",
                getattr(e, "timeout", 0),
                e.cmd,
                len(partial_stdout),
                len(partial_stderr),
            )
            payload = {
                "success": False,
                "returncode": -1,
                "stdout": partial_stdout,
                "stderr": "Command timed out",
                "command": e.cmd,
            }
            self.last_result = payload
            return payload

        except FileNotFoundError:
            # Preserve original return shape
            self.logger.error(
                "Claude command not found in PATH. Confirm installation & PATH configuration."
            )
            payload = {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Claude command not found",
                "command": "claude",
            }
            self.last_result = payload
            return payload

        except Exception as e:
            self.logger.error("Unexpected error executing Claude command: %s", str(e))
            payload = {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "command": 'echo "hello" | claude -p --output-format json',
            }
            self.last_result = payload
            return payload
