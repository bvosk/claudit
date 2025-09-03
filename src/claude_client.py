import subprocess
import logging
import os
from typing import Dict, Any


class ClaudeClient:
    def __init__(self, proxy_port: int = 8080):
        self.proxy_port = proxy_port
        self.proxy_url = f"http://localhost:{proxy_port}"
        self.logger = logging.getLogger(__name__)

    def run_claude_command(self) -> Dict[str, Any]:
        # Set environment variables to route through proxy and disable SSL verification
        env = os.environ.copy()

        # Clear all proxy related environment variables first
        env["HTTP_PROXY"] = ""
        env["HTTPS_PROXY"] = ""
        env["CURL_CA_BUNDLE"] = ""
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        env["PYTHONHTTPSVERIFY"] = "0"
        env["NO_PROXY"] = ""
        env["SOCKS_PROXY"] = ""

        # Set HTTP proxy (hardcoded to http_only configuration)
        env["HTTP_PROXY"] = self.proxy_url
        env["HTTPS_PROXY"] = self.proxy_url

        # Log the environment variables being set
        self.logger.info("Setting environment variables for HTTP proxy:")
        self.logger.info(f"  HTTP_PROXY={env.get('HTTP_PROXY', '')}")
        self.logger.info(f"  HTTPS_PROXY={env.get('HTTPS_PROXY', '')}")

        try:
            # Construct the command with echo and pipe
            cmd = "claude -p hello"

            self.logger.info(f"Executing command: {cmd}")

            # Run the command in shell
            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, timeout=30, shell=True
            )

            # Return result object
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": cmd,
            }

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out: {e.cmd}")
            return {
                "success": False,
                "returncode": -1,
                "stdout": e.stdout.decode() if e.stdout else "",
                "stderr": "Command timed out",
                "command": e.cmd,
            }

        except FileNotFoundError:
            self.logger.error(
                "Claude command not found. Please ensure it's installed and in PATH."
            )
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Claude command not found",
                "command": "claude",
            }

        except Exception as e:
            self.logger.error(f"Error executing Claude command: {str(e)}")
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "command": 'echo "hello" | claude -p --output-format json',
            }


# Configure logging if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
