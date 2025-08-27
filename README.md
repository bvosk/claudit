# Mitmproxy HTTP Capture Setup

This setup uses a pure Python implementation with mitmproxy to capture HTTP requests in a Docker container.

## Quick Start

1. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

2. **View captured requests:**
   ```bash
   cat captures/requests.txt
   ```

## Configuration

Edit the `.env` file to customize:

- `TARGET_URL` - The URL to send requests to (default: https://httpbin.org/get)
- `CURL_HEADERS` - Additional headers (comma-separated, format: "key: value")
- `PROXY_PORT` - Proxy port (default: 8080)
- `CAPTURE_FILE` - Output file path (default: /app/captures/requests.txt)
- `KEEP_RUNNING` - Set to `true` to keep container running for inspection

## Examples

**Capture requests to a custom API:**
```bash
# In .env file:
TARGET_URL=https://api.example.com/endpoint
CURL_HEADERS=Authorization: Bearer your-token,Content-Type: application/json
```

**Keep container running for manual testing:**
```bash
# In .env file:
KEEP_RUNNING=true
```

Then connect to the running container:
```bash
docker exec -it mitmproxy-capture /bin/bash
```

## Output Format

- Captured requests are saved as JSON Lines format to `./captures/requests.txt`
- Each line contains a complete request/response record with:
  - Request: method, URL, headers, content, timestamp
  - Response: status code, headers, content, timestamp
  - Metadata: request ID, duration in milliseconds

## Architecture

- **Pure Python Implementation**: No bash scripts, cleaner error handling
- **Programmatic mitmproxy**: Uses mitmproxy's Python API directly
- **Structured Logging**: Proper Python logging with timestamps
- **JSON Lines Output**: Easy to parse and process

## Development

To extend the capture functionality, modify:
- `src/app.py` - Main application logic
- `src/capture_addon.py` - mitmproxy addon for traffic interception

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

**Use the convenience script:**
```bash
python scripts/format.py --check      # Check formatting
python scripts/format.py --fix        # Format all files
python scripts/format.py --help       # Show help
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
rm -rf captures/
```
