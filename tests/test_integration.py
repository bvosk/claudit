import subprocess
import tempfile
import pytest
from pathlib import Path

from syrupy import PyTestLocation
from syrupy.extensions import AmberSnapshotExtension
from syrupy.types import SnapshotIndex

import app


class ClaudePromptExtension(AmberSnapshotExtension):
    @classmethod
    def get_snapshot_name(
        cls, *, test_location: "PyTestLocation", index: "SnapshotIndex" = 0
    ) -> str:
        return f"claude_prompt"


@pytest.fixture
def latest_snapshot(snapshot):
    return snapshot.use_extension(ClaudePromptExtension)


@pytest.mark.slow
def test_host_generates_markdown(latest_snapshot):
    with tempfile.TemporaryDirectory() as temp_dir:
        test_output_dir = Path(temp_dir) / "test_outputs"
        test_output_dir.mkdir()

        app.main(str(test_output_dir))

        markdown_file = test_output_dir / "claudecode.md"
        assert (
            markdown_file.exists()
        ), f"Expected markdown file not found at {markdown_file}"
        markdown_content = markdown_file.read_text()

        assert len(markdown_content.strip()) > 0, "Generated markdown file is empty"
        assert markdown_content == latest_snapshot


@pytest.mark.slow
def test_docker_container_generates_markdown(latest_snapshot):
    with tempfile.TemporaryDirectory() as temp_dir:
        test_output_dir = Path(temp_dir) / "test_outputs"
        test_output_dir.mkdir()

        run_in_container(test_output_dir)

        markdown_file = test_output_dir / "claudecode.md"
        assert (
            markdown_file.exists()
        ), f"Expected markdown file not found at {markdown_file}"
        markdown_content = markdown_file.read_text()

        assert len(markdown_content.strip()) > 0, "Generated markdown file is empty"
        assert markdown_content == latest_snapshot


@pytest.mark.slow
@pytest.mark.parametrize("claude_code_version", ["1.0.110"])
def test_docker_container_v1_10_110_generates_markdown(claude_code_version, snapshot):
    with tempfile.TemporaryDirectory() as temp_dir:
        test_output_dir = Path(temp_dir) / "test_outputs"
        test_output_dir.mkdir()

        run_in_container(test_output_dir, claude_code_version)

        markdown_file = test_output_dir / "claudecode.md"
        assert (
            markdown_file.exists()
        ), f"Expected markdown file not found at {markdown_file}"
        markdown_content = markdown_file.read_text()

        assert len(markdown_content.strip()) > 0, "Generated markdown file is empty"
        assert markdown_content == snapshot(name="claude_prompt")


def run_in_container(test_output_dir: Path, claude_code_version="latest"):
    try:
        project_root = Path(__file__).parent.parent

        build_cmd = [
            "docker-compose",
            "build",
            "--build-arg",
            f"CLAUDE_CODE_VERSION={claude_code_version}",
            "mitmproxy-capture",
        ]

        build_result = subprocess.run(
            build_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute build timeout
        )

        assert (
            build_result.returncode == 0
        ), f"Docker build failed: {build_result.stderr}"

        # Run the built container with test-specific mounts
        run_cmd = [
            "docker-compose",
            "run",
            "--rm",
            "-v",
            f"{test_output_dir}:/app/prompts",
            "mitmproxy-capture",
        ]

        # Run the container and wait for completion
        result = subprocess.run(
            run_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute runtime timeout
        )

    except subprocess.TimeoutExpired:
        # Clean up any running containers on timeout
        subprocess.run(
            ["docker-compose", "down", "--remove-orphans"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
        )
        raise AssertionError("Docker container timed out after 5 minutes")

    except Exception as e:
        # Clean up any running containers on error
        subprocess.run(
            ["docker-compose", "down", "--remove-orphans"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
        )
        raise e

    finally:
        # Ensure cleanup of any containers
        subprocess.run(
            ["docker-compose", "down", "--remove-orphans"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
        )

    assert result.returncode == 0, f"Docker container failed: {result.stderr}"
