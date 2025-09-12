# Claudit

## Project overview

This setup uses a pure Python implementation with mitmproxy running in reverse proxy mode to capture Anthropic API inference HTTP requests inside a Docker container.

## Usage

Run this project on the host:

```bash
mitm-capture
```

To install development dependencies, run:
```bash
uv sync
```

Run inside the docker container with:

```bash
   docker-compose up --build
```

Remember to first install dependencies:

```bash
uv sync
```

## Testing

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
