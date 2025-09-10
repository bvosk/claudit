# Mitmproxy HTTP Capture Setup

This setup uses a pure Python implementation with mitmproxy running in reverse proxy mode to capture Anthropic API inference HTTP requests inside a Docker container.

## Quick Start

1. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```
2.
   mitm-capture automatically sets `ANTHROPIC_BASE_URL=http://localhost:8080` and runs mitmproxy in reverse mode so all Claude CLI inference requests are routed through (and captured by) the local proxy.

## Architecture

- **Pure Python Implementation**: No bash scripts, cleaner error handling
- **Programmatic mitmproxy**: Uses mitmproxy's Python API directly
- **Structured Logging**: Proper Python logging with timestamps
- **JSON Lines Output**: Easy to parse and process
- **Reverse Proxy Mode**: mitmproxy runs with `--mode reverse:https://api.anthropic.com`, while `ANTHROPIC_BASE_URL=http://localhost:8080` points the Claude CLI at the local proxy so requests are captured without relying on HTTP(S)_PROXY variables.

## Reverse Proxy Mode

The service starts mitmproxy in reverse mode targeting `https://api.anthropic.com` and sets `ANTHROPIC_BASE_URL` to `http://localhost:8080`. The Claude CLI sends inference traffic directly to the proxy host, which forwards upstream while logging `/v1/messages` requests and responses.  The custom base URL is injected automatically.

Captured traffic:
- Written (overwritten per run) to `captures/claudecode.json`
- First captured exchange also rendered to `claudecode.md`

Run your own test prompt inside the container (already done automatically by the entrypoint):
```bash
docker exec -it mitmproxy-capture claude -p "hello" --model haiku
```

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
