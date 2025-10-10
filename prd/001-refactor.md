# Claudit Refactoring Plan

## Objectives
- Separate concerns between proxy orchestration, Claude CLI invocation, capture persistence, and prompt presentation.
- Introduce clear interfaces that allow dependency injection and mocking for unit tests.
- Remove direct file system writes from formatting or capture logic and centralize persistence behind a repository abstraction.
- Preserve current runtime behavior while reducing implicit coupling and improving observability.

## Guiding Principles
- Prefer small, testable classes with explicit inputs/outputs over monolithic orchestrators.
- Use `typing.Protocol` or abstract base classes to define interaction contracts between layers.
- Keep I/O at the edges; business logic should operate on domain objects (e.g., `Prompt`, capture DTOs).
- Maintain backward compatibility for CLI entry points while refactoring internals incrementally.
- Support multiple agents via a strategy pattern so new agents can be added without touching shared orchestration code.

## Architecture Overview
- **Agent Strategy Layer**
  - `AgentStrategy` protocol defines the contract for CLI invocation, API interception rules, prompt extraction, and tool description handling.
  - Concrete strategies (`ClaudeCodeStrategy` first) encapsulate agent-specific behavior.
  - Optional registry/factory maps agent identifiers to strategy instances for wiring through configuration or CLI flags.
- **Infrastructure Layer**
  - `MitmproxyRunner`: owns mitmproxy lifecycle (setup/start/stop) and surfaces async context manager/explicit start-stop methods.
  - `ClaudeCommandRunner` → generalized `AgentCommandRunner` that delegates to the active `AgentStrategy` for command/timeout/env overrides.
  - `CaptureSink` protocol + implementations (`InMemoryCaptureSink`, `JsonFileCaptureSink`) to centralize persistence.
- **Domain Layer**
  - `CaptureRepository`: coordinates data flow from mitmproxy addon into sinks and exposes normalized capture DTOs per agent.
  - `PromptExtractor`: strategy-aware component that delegates to `AgentStrategy` for parsing API payloads into `Prompt` objects.
  - `PromptRenderer`: formats prompts (existing formatter reused).
  - `PromptWriter`: handles Markdown/file emission to keep formatting pure.
- **Application Layer**
  - `CaptureWorkflowService`: orchestrates proxy startup, CLI invocation, capture retrieval, prompt extraction, scrubbing, rendering, and writing using injected dependencies and active strategy.
  - CLI (`app.py`) becomes lightweight composition root: selects strategy, instantiates concrete infrastructure pieces, invokes workflow.

## Desired Directory Structure
```
src/
  agents/
    __init__.py
    base.py                 # defines AgentStrategy protocol and shared utilities
    registry.py             # maps agent identifiers to strategy instances
    claude_code/
      __init__.py
      strategy.py           # ClaudeCodeStrategy implementation
      command.py            # CLI command/builders unique to Claude Code
      prompt_parser.py      # request → Prompt extraction logic
  application/
    __init__.py
    capture_service.py      # CaptureWorkflowService implementation
  domain/
    __init__.py
    prompts/
      __init__.py
      extractor.py          # Strategy-aware PromptExtractor
      renderer.py           # PromptRenderer (existing)
      writer.py             # PromptWriter handling filesystem output
  infrastructure/
    __init__.py
    mitmproxy_runner.py     # MitmproxyRunner async lifecycle management
    command_runner.py       # AgentCommandRunner invoking strategy-provided CLI commands
    capture/
      __init__.py
      repository.py         # CaptureRepository coordinating addon + sinks
      sinks/
        __init__.py
        in_memory.py        # InMemoryCaptureSink implementation
        json_file.py        # JsonFileCaptureSink implementation
  presentation/
    __init__.py
    cli.py                  # app.py composition root (could remain at top-level if preferred)
```
- `tests/agents/claude_code/` mirrors agent directory for strategy-specific tests.
- Shared test fixtures live under `tests/support/` to avoid cross-agent coupling.

## Implementation Roadmap
1. **Baseline & Safety Nets**
   - Document current behaviors (CLI invocation, capture writing, prompt rendering) and enumerate invariants.
   - Expand/author unit tests for existing prompt extraction, content scrubbing, and capture serialization.
   - Add smoke/integration tests around current workflow if feasible ( guard against regressions during refactor ).

2. **Introduce Agent Strategy Contracts**
   - Define `AgentStrategy` protocol with responsibilities:
     - `name`/metadata.
     - `command`/`environment_overrides` (for CLI execution).
     - `api_hosts`/`path_matchers` (for mitmproxy filtering).
     - `extract_prompt(capture: dict) -> Prompt` and helper hooks.
   - Provide `ClaudeCodeStrategy` implementation replicating current behavior and tests covering command/env/prompt extraction logic.

3. **Refactor Prompt Processing**
   - Create strategy-aware `PromptExtractor` that requests prompt data via `strategy.extract_prompt`.
   - Move existing `ClaudeClient.extract_prompt` behavior into `ClaudeCodeStrategy` or helper and delete redundant methods from command runner.
   - Introduce `PromptWriter` to encapsulate Markdown file I/O; update `app.py` to use it.

4. **Decouple Command Execution**
   - Rename/reshape `ClaudeClient` into `AgentCommandRunner` that:
     - relies on injected `AgentStrategy` for command/env/timeouts/post-processing.
     - maintains stdout/stderr scrubbing via strategy-provided hooks (retain current tooling-block scrub for Claude Code).
   - Patch tests to cover strategy-driven invocation using mocks for `subprocess.run`.

5. **Isolate Capture Persistence**
   - Introduce `CaptureSink` and `CaptureRepository`.
   - Refactor `CaptureAddon` to depend on a repository (constructor injection) instead of performing file writes directly.
   - Allow repository to apply agent strategy filters (only store flows matching strategy-defined endpoints) and write via sink.
   - Add tests with fake flows verifying filtering and persistence.

6. **Rework Proxy Orchestration**
   - Extract mitmproxy lifecycle responsibilities into `MitmproxyRunner`; integrate readiness checks and shutdown logic there.
   - Update workflow service to use runner with async context, keeping capture gathering logic centralized.
   - Provide tests leveraging mocks/fakes for event loop interactions.

7. **Compose Capture Workflow Service**
   - Build `CaptureWorkflowService` composing runner, command runner, repository, prompt extractor, renderer, writer, and content scrubber.
   - Ensure service accepts an `AgentStrategy` (or identifier → strategy lookup) to enable multi-agent support.
   - Update `app.py` to instantiate concrete strategy (currently `ClaudeCodeStrategy`) and pass to service.
   - Create integration-style test using fakes to ensure correct orchestration without invoking real mitmproxy/CLI.

8. **Cleanup & Documentation**
   - Remove legacy `MitmproxyCapture` and obsolete utilities.
   - Update CLI docs (`CLAUDE.md`, README) to describe new architecture and how to add agents.
   - Ensure `mise` tasks remain accurate; update Usage instructions if tasks change.

## Testing Strategy
- Unit tests for each new class, emphasizing strategy behavior and dependency injection.
- Snapshot tests for prompt rendering to ensure Markdown stability.
- Integration/cohesion tests for `CaptureWorkflowService` with stubbed strategies, command runner, and repository.
- `mise test` for quick checks; `mise test-all` before major merges or releases.

## Risks & Mitigations
- **Strategy misconfiguration**: provide clear defaults and validation when selecting agents.
- **Proxy lifecycle regressions**: cover runner with async tests; manual verification within container.
- **Command invocation differences**: rely on strategy-provided command/env/timeouts; unit-test each agent's runner behavior.
- **Large refactor scope**: execute phases sequentially, merging behind green tests; keep feature toggles if necessary.

## Decisions (Open Questions Resolved)
- **Agent selection**: Execute all registered agents sequentially for each run; no user selection required initially.
- **Streaming/concurrency**: No streaming capture or concurrent session support needed; focus on single-session workflow.
- **Sink behavior**: Provide separate sinks per agent (e.g., distinct files/backends) to keep artifacts isolated.
- **Transport assumptions**: All agents operate over HTTP; no alternate capture mechanisms needed.

## Step 1 Progress – Baseline Notes
- **CLI invocation**: `ClaudeClient.run_claude_command` builds env vars `ANTHROPIC_BASE_URL=http://localhost:{port}` and dummy `ANTHROPIC_API_KEY`, runs a non-fatal `claude -v` preflight, then executes the hard-coded `claude -p hello --model haiku` command with `timeout=15s`. Both stdout/stderr are scrubbed with `_scrub_dynamic_tooling_section` to remove the dynamic "You can use the following tools…" block before persisting to `last_result`.
- **Capture persistence**: `CaptureAddon` writes each qualifying flow to `captures/claudecode.json` (overwriting per event) while also appending to in-memory `captured_data`. Responses are filtered to `api.anthropic.com/v1/messages`, timestamps derive from mitmproxy's `timestamp_start`, and sensitive headers (e.g., `x-api-key`) are masked by prefix retention.
- **Prompt extraction**: `ClaudeClient.extract_prompt` uses the newest capture (`captured_data[0]`), accepts JSON strings or dict payloads, enforces dict content, and lifts `system`/`tools` lists into a `Prompt` dataclass with metadata containing `source='claude_client'`, `capture_id`, request URL, and method. Timestamp parsing tolerates ISO strings with optional `Z` suffix and falls back to `datetime.now(timezone.utc)`.
- **Runtime workflow**: `app.py` orchestrates the flow—launches `MitmproxyCapture.capture_and_return()`, feeds the result back into `ClaudeClient.extract_prompt`, sanitizes via `ClaudeContentScrubber.scrub_prompt_data`, formats with `render_prompt_markdown`, and writes to `prompts/claudecode.md` (creating the directory if missing). All stdout/stderr during capture is trapped to keep CLI output clean.
- **Mitmproxy lifecycle**: `MitmproxyCapture` configures reverse proxy mode targeting `https://api.anthropic.com`, asserts port availability, clears addon state per session, waits for readiness before offloading the Claude CLI to a thread, then triggers `master.shutdown()` and ensures graceful teardown (with timeout + cancel fallback) while sleeping 0.5s to release the socket.
