# Claudit

## Project overview

This setup uses a pure Python implementation with mitmproxy running in reverse proxy mode to capture Anthropic API inference HTTP requests inside a Docker container.

## Tools

- Package manager: [uv](https://docs.astral.sh/uv/)
- Testing: [pytest](https://docs.pytest.org/)
- Snapshots: [syrupy](https://github.com/tophat/syrupy)
- Task runner: [mise](https://mise.jdx.dev/)
- Formatter: [black](https://black.readthedocs.io/)

## Usage

This project uses `mise` as a task runner. To see available tasks, run:

```
> mise tasks
Name                   Description
install                Install development dependencies
run-container          Run inside docker container with build
run-container-build    Run inside docker container
run-host               Run mitm-capture on the host
test                   Run tests (excluding slow tests)
test-all               Run all tests including slow tests
test-update-snapshots  Update snapshots when output changes
test-verbose           Run tests with verbose output
```

**Run tests:**
```bash
uv run pytest -m "not slow"
```

This skips tests marked as slow. To include slow tests, run:

```bash
uv run pytest
```

**Run with verbose output:**
```bash
uv run pytest -v
```

**Update snapshots when output changes:**
```bash
uv run pytest --snapshot-update
```

Run slow tests only to validate your final work. Between edits, skipping slow tests is recommended.
