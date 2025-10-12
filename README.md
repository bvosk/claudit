# Mitmproxy HTTP Capture Setup

This setup uses a pure Python implementation with mitmproxy running in reverse proxy mode to capture Anthropic API inference HTTP requests inside a Docker container.

## Quick Start

1. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

## Architecture

- **CaptureService orchestration**: `claudit.application.capture_service.CaptureService` wires the agent strategy, mitmproxy runner, capture repository, prompt extractor, scrubber, renderer, and writer behind a single async workflow.
- **Programmatic mitmproxy**: `MitmproxyRunner` wraps mitmproxy's Python API and exposes an async context manager that handles startup, readiness polling, shutdown, and socket release.
- **Repository-backed persistence**: `CaptureRepository` funnels qualifying flows into strategy-specific sinks (JSON file for artefacts, in-memory list for prompt extraction).
- **Strategy-driven commands**: `AgentCommandRunner` executes the active agent's CLI with injected proxy environment variables and stdout/stderr scrubbing.
- **Structured Logging**: Centralised Python logging keeps mitmproxy chatter out of the console while surfacing workflow updates.
- **Reverse Proxy Mode**: mitmproxy still runs in `reverse:https://api.anthropic.com`; `CaptureService.build()` configures the runner and command runner so the Claude CLI targets `http://localhost:8080` without mutating proxy environment variables.

## Reverse Proxy Mode

The service starts mitmproxy in reverse mode targeting `https://api.anthropic.com` and sets `ANTHROPIC_BASE_URL` to `http://localhost:8080`. The Claude CLI sends inference traffic directly to the proxy host, which forwards upstream while logging `/v1/messages` requests and responses.  The custom base URL is injected automatically.

Captured traffic:
- Persisted to `captures/<agent>.json`
- Latest prompt rendered to `prompts/<agent>.md`

### Testing

This project uses [uv](https://docs.astral.sh/uv/) for package management and testing with [syrupy](https://github.com/tophat/syrupy) for snapshot testing:

**Run all tests:**
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

**Install development dependencies:**
```bash
uv sync
```

The test suite includes:
- **Docker integration test**: Full end-to-end testing of the Docker container workflow using snapshot testing to validate generated markdown output
- **Snapshot testing**: Uses syrupy to compare generated outputs against known good values, making it easy to detect changes and update expectations

### CI

To test GH action runs on current branch, run:

```sh
gh workflow run daily-prompt-tracker.yml -r "$(git branch --show-current)"
```

### Code Formatting

This project uses [Black](https://black.readthedocs.io/) for consistent Python code formatting:

**Check if files need formatting:**
```bash
uv run black --check .
```

**Format all Python files:**
```bash
uv run black .
```


**Pre-commit hooks:**
The project includes pre-commit hooks that automatically run Black on commits:
```bash
uv run pre-commit install      # Install hooks
uv run pre-commit run --all-files  # Run all hooks manually
```

Black is configured in `pyproject.toml` with:
- Line length: 88 characters
- Target Python version: 3.8+
- Excludes common directories (`.git`, `__pycache__`, etc.)

## Cleanup

```bash
docker-compose down
```
