# Claudit

## Project overview

This setup uses a pure Python implementation with mitmproxy running in reverse proxy mode to capture Anthropic API inference HTTP requests inside a Docker container.

## Development Tools

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
format                 Format code with black
install                Install development dependencies
run-container          Run inside docker container with build
run-container-build    Run inside docker container
run-host               Run mitm-capture on the host
test                   Run tests (excluding slow tests)
test-all               Run all tests including slow tests
test-update-snapshots  Update snapshots when output changes
test-verbose           Run tests with verbose output
typecheck              Typecheck code with basedpyright
```

## Agent Instructions

### Tests

- Use `mise test-all` to verify all major changes. If the tests fail, immediately STOP and fix the failing tests.

### Mise tasks

- You MUST use `mise` to run all routine tasks. Check if there is a configured `mise` tasks before running any bash commands.
- Whenever the mise tasks are updated, you MUSt update the "Usage" section of this file to reflect the changes.

### Code Style

- The `black` formatter is used to format all Python code
- Filenames should always match up with the classes they define. For example the class `AgentStrategy` should be in a file called `agent_strategy.py`
