import subprocess
import logging
import os
import shutil
import re
from typing import Dict, Any


class ClaudeClient:

    def __init__(self, proxy_port: int = 8080):
        self.proxy_port = proxy_port
        self.proxy_url = f"http://localhost:{proxy_port}"
        self.logger = logging.getLogger(__name__)
        self.last_result: Dict[str, Any] | None = None
        # Precompile pattern that identifies the dynamic "You can use the following tools..." section
        # We'll remove from that line down to the first blank line that follows, to stabilize snapshots.
        self._tools_block_start_pattern = re.compile(
            r"^You can use the following tools", re.MULTILINE
        )

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

    def _scrub_dynamic_tooling_section(self, text: str) -> str:
        """
        Remove the dynamic capability/tool listing section that begins with
        'You can use the following tools...' because its contents vary based
        on repo state and would cause unstable snapshot outputs.
        Strategy:
          - Find the starting line (regex anchored to start of line)
          - Remove through the next blank line (double newline) or end of text
        """
        if not text:
            return text
        match = self._tools_block_start_pattern.search(text)
        if not match:
            return text
        start = match.start()
        # Find the next double newline after start
        remainder = text[start:]
        split_index = remainder.find("\n\n")
        if split_index == -1:
            # Remove everything from start if no terminating blank line
            return text[:start].rstrip() + "\n"
        # splice out the dynamic block
        cleaned = text[:start] + remainder[split_index + 2 :]
        return cleaned.lstrip("\n")

    @staticmethod
    def scrub_prompt_text(text: str) -> str:
        """
        Public static helper for scrubbing dynamic tool capability sections from
        captured Anthropic/Claude prompt text prior to formatting or snapshotting.

        Unlike _scrub_dynamic_tooling_section (which is instance-based and
        operates on CLI stdout/stderr), this static method can be imported and
        applied to request/response payloads (e.g. in the formatter) without
        instantiating a ClaudeClient.

        It performs a conservative removal of any block that starts with the
        canonical lead-in line and extends until a blank line or end of text.
        """
        pattern = re.compile(
            r"^You can use the following tools.*?(?:\n\n|\Z)", re.MULTILINE | re.DOTALL
        )
        return re.sub(pattern, "", text)

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
        raw_stdout = subprocess_result.stdout or ""
        raw_stderr = subprocess_result.stderr or ""
        cleaned_stdout = self._scrub_dynamic_tooling_section(raw_stdout)
        cleaned_stderr = self._scrub_dynamic_tooling_section(raw_stderr)
        payload = {
            "success": subprocess_result.returncode == 0,
            "returncode": subprocess_result.returncode,
            "stdout": cleaned_stdout,
            "stderr": cleaned_stderr,
            "command": cmd,
        }
        self.last_result = payload
        return payload
