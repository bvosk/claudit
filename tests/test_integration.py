import subprocess
import tempfile
import pytest
from pathlib import Path


@pytest.mark.slow
def test_docker_container_generates_markdown(snapshot):
    # Create a temporary directory for test outputs
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
        assert markdown_content == snapshot


def run_in_container(test_output_dir: Path):
    try:
        project_root = Path(__file__).parent.parent

        claude_code_version = "1.0.110"  # Pinned for consistency
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
