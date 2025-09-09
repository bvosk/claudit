# Mitmproxy HTTP Capture Setup

This setup uses a pure Python implementation with mitmproxy to capture HTTP requests in a Docker container.

## Quick Start

1. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

## Architecture

- **Pure Python Implementation**: No bash scripts, cleaner error handling
- **Programmatic mitmproxy**: Uses mitmproxy's Python API directly
- **Structured Logging**: Proper Python logging with timestamps
- **JSON Lines Output**: Easy to parse and process

### Testing

This project uses [uv](https://docs.astral.sh/uv/) for package management and testing:

**Run all tests:**
```bash
uv run pytest
```

**Run with verbose output:**
```bash
uv run pytest -v
```

**Run specific test:**
```bash
uv run pytest tests/test_e2e_capture.py::TestMitmproxyCapture::test_end_to_end_capture -v
```

**Install development dependencies:**
```bash
uv sync
```

The test suite includes:
- End-to-end capture workflow testing
- Custom headers validation
- Configuration loading verification
- Mock HTTP server integration for isolated testing

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
