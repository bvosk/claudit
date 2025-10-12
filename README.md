# Claudit

A toolkit for capturing coding agent system prompts. Claudit uses HTTP inference traffic via a reverse mitmproxy, extracting structured prompt artifacts, and rendering them to Markdown for review.

## Key Features

- Reverse-mode mitmproxy orchestration
- Strategy pattern for agent-specific CLI invocation & prompt extraction
- Deterministic prompt scrubbing (date redaction, etc.)
- Markdown prompt rendering via Jinja2 templates
- Pluggable capture sinks (JSON file / in‑memory)
- Async orchestration with clean startup / readiness / shutdown
- Snapshot & integration tests (pytest + syrupy)
- Task automation via [`mise`](https://mise.jdx.dev/) & dependency management with [`uv`](https://docs.astral.sh/uv/)
- Centralized, noise-filtered logging

## At a Glance (TL;DR)

1. `docker-compose up --build`
2. Run Claude CLI inside container; traffic flows through proxy.
3. Inspect `captures/claudecode.json` & `prompts/claudecode.md`.
4. Run `mise test-update-snapshots` after intentional changes.
5. Extend via new `AgentStrategy` implementations.

Happy capturing.

---

## Quick Start (Container)

1. Build & run (forces rebuild on changes):
   ```bash
   docker-compose up --build
   ```
2. Proxy listens on: `http://localhost:8080`
3. The Claude CLI (inside container) is pointed at the proxy via `ANTHROPIC_BASE_URL`.

Stop & remove:
```bash
docker-compose down
```

### Artifacts Produced

| File | Description | Update Policy |
|------|-------------|---------------|
| `captures/claudecode.json` | Latest qualifying HTTP exchange (overwrites each run) | Overwrite |
| `prompts/claudecode.md` | Rendered system/tools prompt extracted from capture | Overwrite |

> NOTE: Current JSON sink only keeps the *last* stored capture. If you need *all* captures per run, add or swap in an append/list sink.

---

## Quick Start (Host Execution)

Prerequisites: Python ≥3.8, `uv` installed.

```bash
mise install          # Installs dev dependencies (uv sync)
mise run-host         # Runs console entrypoint (mitm-capture)
```

Ensure you export a real `ANTHROPIC_API_KEY` (the strategy sets a dummy key if none exists, which won’t yield real responses).

---

## Task Automation (mise)

List tasks:
```bash
mise tasks
```

| Task | Description |
|------|-------------|
| install | Install development dependencies |
| run-host | Run mitm-capture on the host |
| run-container | Run inside docker container with build |
| run-container-build | Run inside docker container (no build) |
| test | Run tests excluding slow tests |
| test-all | Run all tests (including slow) |
| test-verbose | Run tests verbosely |
| test-update-snapshots | Update changed snapshots |
| typecheck | Static type checking (basedpyright) |
| format | Format code with Black |

Examples:
```bash
mise test
mise test-all
mise typecheck
mise format
mise test-update-snapshots
```

Always prefer tasks to ad‑hoc commands so CI/local parity is maintained.

---

## Project Structure

```
.
├── docker-compose.yml
├── Dockerfile
├── mise.toml
├── pyproject.toml
├── src/claudit/
│   ├── app.py                        # Console entrypoint
│   ├── application/capture_service.py
│   ├── agents/
│   │   ├── agent_strategy.py         # Strategy protocol
│   │   └── claude_code/claude_code_strategy.py
│   ├── infrastructure/
│   │   ├── mitmproxy_runner.py       # Lifecycle + readiness
│   │   ├── agent_command_runner.py   # CLI execution
│   │   ├── capture/
│   │   │   ├── repository.py
│   │   │   └── sinks/{json_file,in_memory}.py
│   ├── domain/prompts/{prompt_extractor.py,prompt_writer.py}
│   ├── capture_addon.py              # mitmproxy addon hook
│   ├── prompt_formatter.py           # Jinja2 renderer
│   └── models.py                     # Config + capture models
├── templates/claudecode.md           # Markdown template
├── captures/                         # Latest JSON capture
└── prompts/                          # Rendered Markdown prompt
```

---

## Architecture Overview

1. `CaptureService.run()` orchestrates the workflow:
   - Reset repository.
   - Start reverse mitmproxy (async context).
   - Execute agent CLI (`AgentCommandRunner`) with injected proxy env.
   - Collect qualifying flows through `CaptureAddon` → `CaptureRepository`.
   - Extract domain `Prompt` via `PromptExtractor` & strategy logic.
   - Scrub prompt (`strategy.scrub_prompt()`).
   - Render Markdown (`prompt_formatter.render_prompt_markdown`).
   - Persist artefact (`PromptWriter`).
2. `MitmproxyRunner` manages:
   - Port sanity / availability
   - Startup and readiness polling
   - Graceful shutdown & socket release
3. Strategy (`AgentStrategy`) defines:
   - CLI command & version preflight
   - Host/path filters
   - Extraction & scrubbing semantics
   - Environment overrides (pointing base URL to proxy)
4. Capture persistence:
   - In‑memory list inside `CaptureRepository`
   - One-file JSON sink (current run’s last capture)

---

## Capture Semantics & Filtering

The default Claude Code strategy filters:
- Hosts: `api.anthropic.com`
- Path prefixes: `/v1/messages`

A flow is persisted only if both host and path criteria pass. Header masking is applied (API keys, auth tokens, etc.). Content bodies are decoded (attempt JSON, fallback to text, else sized binary marker).

> Duplicate header masking logic appears both in `capture_addon` and model helpers; future consolidation is planned.

---

## Prompt Extraction & Scrubbing

Claude Code strategy:
- Extracts `system` array text entries.
- Collects `tools` definitions verbatim.
- Scrubs date lines: `Today's date: YYYY-MM-DD` → `Today's date: [date]`.

You can implement custom redaction (IDs, timestamps, emails) in `scrub_prompt()` for deterministic snapshot comparisons.

---

## Template Rendering

Jinja2 template: `templates/claudecode.md`

Variables provided:
- `system`: list of `{ type: text, text: ... }`
- `tools`: list of raw tool objects (rendered with JSON filter in template)

To introduce a new template:
- Add file to `templates/`
- Provide a custom renderer or extend `prompt_formatter.py`

---

## Testing

Run:
```bash
mise test
```

Full (including slow / integration):
```bash
mise test-all
```

Update snapshots:
```bash
mise test-update-snapshots
```

Verbose:
```bash
mise test-verbose
```

Snapshot testing (syrupy) detects prompt drift. Only update snapshots after validating the change is intentional.

Missing (recommended additions):
- Unit tests for `CaptureRepository._should_store()` edge cases
- Tests for `MitmproxyRunner.wait_until_ready()` timeout path
- Scrubbing edge cases (multi-date lines)
- JSON sink behavior (overwrite vs expected semantics)

---

## Type Checking

```bash
mise typecheck
```

Configured via basedpyright (`pyproject.toml`).

---

## Formatting & Pre-Commit

Format:
```bash
mise format
```

Pre-commit:
```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

`pyproject.toml` configures Black (line length 88, Python target 3.8).

---

## Logging

Environment variable `LOG_LEVEL` (e.g. `DEBUG`, `INFO`) influences root logger. Mitmproxy, asyncio, urllib3 log levels are reduced for clarity. All workflow phases log concise messages.

---

## Configuration & Environment

| Variable | Purpose | Default / Source |
|----------|---------|------------------|
| LOG_LEVEL | Overall logging level | INFO (compose sets DEBUG fallback) |
| ANTHROPIC_API_KEY | Real Claude key (for live traffic) | DUMMY (strategy override) |
| ANTHROPIC_BASE_URL | Injected to redirect CLI to proxy | Set automatically |
| Port | Proxy listen port | 8080 (override in `CaptureService.build`) |

Add a `.env` file for Docker usage:
```
ANTHROPIC_API_KEY=sk-your-key
LOG_LEVEL=INFO
```

---

## Docker Build Arguments

| ARG | Description | Example |
|-----|-------------|---------|
| MITMPROXY_TAG | Pin mitmproxy base image | `--build-arg MITMPROXY_TAG=10.3.0` |
| CLAUDE_CODE_VERSION | Pin Claude CLI version | `--build-arg CLAUDE_CODE_VERSION=latest` |

Build manually:
```bash
docker build \
  --build-arg MITMPROXY_TAG=10.3.0 \
  --build-arg CLAUDE_CODE_VERSION=2024.09.01 \
  -t mitm-capture .
```

---

## Adding a New Agent Strategy

1. Create: `src/claudit/agents/<agent_id>/<agent_id>_strategy.py`
2. Implement `AgentStrategy`:
   - `name`
   - `command()`
   - `version_command()` (optional)
   - `environment_overrides(proxy_port)`
   - `api_hosts()`
   - `api_path_prefixes()`
   - `extract_prompt(captured_data)`
   - `scrub_prompt(prompt)`
3. Use it:
```python
from claudit.application.capture_service import CaptureService
from claudit.agents.my_agent.my_agent_strategy import MyAgentStrategy
from claudit.prompt_formatter import render_prompt_markdown

service = CaptureService.build(
    strategy=MyAgentStrategy(),
    content_scrubber=lambda p: p,
    prompt_renderer=render_prompt_markdown,
)
# await service.run() in an async context
```
4. Add tests for extraction & scrubbing.

---

## Troubleshooting

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Port already in use | Stale proxy / other process | Kill process or change port in `CaptureService.build(proxy_port=...)` |
| No captures written | Filters exclude host/path | Verify strategy host/path; enable DEBUG logging |
| Empty prompt | Request lacked `system` field | Inspect raw request content in capture JSON |
| Readiness timeout | Slow startup / port conflict | Increase `ready_timeout` or free port |
| Markdown not produced | No qualifying capture | Ensure CLI actually performed a network call |
| Masking incomplete | Unanticipated header name | Extend sensitive headers set |

---

## Security Notes

- Header masking is best-effort; treat artefacts as potentially sensitive.
- Avoid committing real API keys.
- Future enhancements recommended:
  - Regex-based body redaction
  - Configurable body capture toggle
  - Append-only audit trail with rotation

---

## Acknowledgements

- [mitmproxy](https://mitmproxy.org/)
- [uv](https://docs.astral.sh/uv/)
- [pytest](https://docs.pytest.org/)
- [syrupy](https://github.com/tophat/syrupy)
- [mise](https://mise.jdx.dev/)

---
