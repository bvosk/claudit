"""Tests for AgentClient command execution."""

import subprocess
from unittest.mock import patch

from claudit.agent_client import AgentClient
from claudit.agents.base import CommandSpec


class _DummyStrategy:
    name = "dummy"

    def __init__(self, version_spec: CommandSpec | None):
        self._version_spec = version_spec

    def command(self) -> CommandSpec:
        return CommandSpec(
            command="echo main",
            use_shell=True,
            timeout_seconds=12.0,
        )

    def version_command(self) -> CommandSpec | None:
        return self._version_spec

    def environment_overrides(self, proxy_port: int) -> dict[str, str]:
        return {"DUMMY_PROXY_PORT": str(proxy_port)}

    def api_hosts(self):
        return ()

    def api_path_prefixes(self):
        return ()

    def scrub_cli_output(self, text: str) -> str:
        return text


class TestAgentClientRunCommand:
    def test_run_agent_command_uses_strategy_version_command(self):
        version_spec = CommandSpec(
            command="tool --version",
            use_shell=False,
            timeout_seconds=7.0,
        )
        strategy = _DummyStrategy(version_spec=version_spec)
        client = AgentClient(strategy=strategy)

        with patch("claudit.agent_client.subprocess.run") as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=version_spec.command,
                    returncode=0,
                    stdout="1.2.3\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args="echo main",
                    returncode=0,
                    stdout="done",
                    stderr="",
                ),
            ]

            result = client.run_agent_command()

        assert mock_run.call_count == 2

        version_call = mock_run.call_args_list[0]
        assert version_call.args[0] == version_spec.command
        assert version_call.kwargs["shell"] is version_spec.use_shell
        assert version_call.kwargs["timeout"] == version_spec.timeout_seconds
        assert version_call.kwargs["env"]["DUMMY_PROXY_PORT"] == str(client.proxy_port)

        main_call = mock_run.call_args_list[1]
        assert main_call.args[0] == "echo main"
        assert main_call.kwargs["shell"] is True
        assert main_call.kwargs["timeout"] == strategy.command().timeout_seconds
        assert result["command"] == "echo main"

    def test_run_agent_command_skips_preflight_when_strategy_has_no_version(self):
        strategy = _DummyStrategy(version_spec=None)
        client = AgentClient(strategy=strategy)

        with patch("claudit.agent_client.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args="echo main",
                returncode=0,
                stdout="done",
                stderr="",
            )

            client.run_agent_command()

        assert mock_run.call_count == 1
        call = mock_run.call_args_list[0]
        assert call.args[0] == "echo main"
