import subprocess
import tempfile
from pathlib import Path


def test_docker_container_generates_markdown(snapshot):
    # Create a temporary directory for test outputs
    with tempfile.TemporaryDirectory() as temp_dir:
        test_output_dir = Path(temp_dir) / "test_outputs"
        test_output_dir.mkdir()

        claude_code_version = "1.0.110"  # Pinned for consistency

        try:
            project_root = Path(__file__).parent.parent

            # Build the Docker container with pinned Claude Code version
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

            # Check that the container ran successfully
            assert result.returncode == 0, f"Docker container failed: {result.stderr}"

            # Check that the markdown file was generated
            markdown_file = test_output_dir / "claudecode.md"
            assert (
                markdown_file.exists()
            ), f"Expected markdown file not found at {markdown_file}"

            # Read the generated markdown content
            markdown_content = markdown_file.read_text()

            # Assert that the content is not empty
            assert len(markdown_content.strip()) > 0, "Generated markdown file is empty"

            # Use syrupy snapshot testing to validate the output
            assert markdown_content == snapshot

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
