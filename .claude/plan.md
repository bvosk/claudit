# Comprehensive Refactor Plan: Decoupled Architecture with TDD

## Current Issues Identified
- **Mixed responsibilities**: `MitmproxyCapture` manages proxy, Claude client, and file I/O
- **Tight coupling**: Claude-specific logic scattered across multiple files
- **No clear interfaces**: Components directly access each other's internals
- **Limited testability**: Hard to unit test individual layers
- **File I/O mixing**: `PromptFormatter` handles both formatting and file writing

## New Architecture Design

### Layer 1: `app.py` - Application Coordinator
**Responsibility**: Top-level orchestration only  
- **Input**: Command line args/config  
- **Output**: Exit code/status  
- **Dependencies**: All other layers (through interfaces)

### Layer 2: `mitm_capture.py` - Generic MITM Proxy
**Responsibility**: Pure proxy setup and traffic capture  
- **Input**: `ProxyConfig` (port, target_url, addon)  
- **Output**: List of `CapturedRequest` objects  
- **No Claude-specific logic**: Generic for any target URL

### Layer 3: `capture_addon.py` - Traffic Filtering & Capture
**Responsibility**: Filter and capture relevant HTTP traffic  
- **Input**: `CaptureConfig` (target patterns, sensitive headers)  
- **Output**: Structured `CapturedRequest` objects  
- **Generic**: Works for any API, not just Anthropic

### Layer 4: `claude_client.py` - Claude CLI Interface
**Responsibility**: All Claude-specific behavior  
- **Input**: Claude command configuration  
- **Output**: Execution result  
- **Encapsulates**: Anthropic URLs, env vars, CLI specifics  
- **Now includes**: Scrubbing of dynamic tool capability section to stabilize snapshots

### Layer 5: `prompt_formatter.py` - Pure Formatting (Target State)
**Responsibility**: Data transformation only  
- **Input**: Structured prompt data / `CapturedRequest`  
- **Output**: Formatted markdown string  
- **No I/O**: (Planned) — file writing moves to `app.py`  
- **Current status**: Still performs file I/O; partial scrubbing logic added

## TDD Implementation Steps

### Phase 1: Create Core Interfaces & Models (Completed)
1. Create `models.py` with data classes:
   - `CapturedRequest`, `ProxyConfig`, `CaptureConfig`
2. Write tests first for validation
3. Implement models to pass tests

### Phase 2: Refactor `prompt_formatter.py` (In Progress)
1. Write unit tests using pytest-mock for template loading
2. Extract pure formatting function (return string)
3. Move file I/O to app coordinator
4. Mock `jinja2.Environment` for isolated tests
5. (Done) Introduced system prompt scrubbing via `ClaudeClient.scrub_prompt_text`
6. (Pending) Replace current class with pure functional API or slim wrapper

### Phase 3: Refactor `capture_addon.py` (Planned)
1. Replace in-place dict building with `CapturedRequest.from_flow`
2. Inject `CaptureConfig`
3. Remove hard-coded Anthropic filtering (make pattern driven)
4. Stop writing to disk; return in-memory list only

### Phase 4: Refactor `mitm_capture.py` (Planned)
1. Accept `ProxyConfig` + injected addon instance
2. Remove direct Claude client dependency
3. Expose start/stop/capture lifecycle returning `List[CapturedRequest]`
4. Add tests with mitmproxy object mocking

### Phase 5: Harden `claude_client.py` (Partially Done)
1. Add pytest-subprocess tests for `claude -v` and prompt run
2. Support configurable prompt, model, timeout
3. Already: environment isolation + dynamic section scrubbing
4. Expose clean interface returning structured result

### Phase 6: Simplify `app.py`
1. Orchestrate: build configs → run proxy → run client → collect captures
2. Use formatter pure function → write files
3. Provide CLI args for model, prompt, output paths
4. Add integration tests (mock boundaries)

## Testing Strategy
- **Models**: Pure unit tests (DONE)
- **Formatter**: Mock Jinja2; assert deterministic markdown (PENDING)
- **Capture Addon**: Fake flow objects; assert filtering/masking (PENDING)
- **Proxy Layer**: Mock DumpMaster lifecycle (PENDING)
- **Claude Client**: pytest-subprocess for version + run paths (PENDING)
- **Integration**: Ensure pipeline composes; snapshot stable (PARTIAL—Docker snapshot updated)
- **Snapshot Stability**: Achieved by scrubbing dynamic tool capability block

## Dependencies
(Completed)
- Added `pytest-subprocess`
- Added `pytest-mock`

## Benefits of New Architecture
- Extensible, testable, fast, maintainable, configurable, TDD-driven, reliable

## Implementation Progress

### Phase 1: ✅ Complete
- [x] `models.py` with `ProxyConfig`, `CaptureConfig`, `CapturedRequest`
- [x] Full validation & parsing logic
- [x] Comprehensive tests (21 passing)
- [x] Timezone-aware timestamps

### Phase 2: 🔄 In Progress
- [x] Added dev test dependencies
- [x] Snapshot stabilization via dynamic section scrubbing
- [ ] Extract pure formatting (currently still writes file)
- [ ] Formatter unit tests (template mocked)
- [ ] Separate file I/O into `app.py`

### Phase 3: ⏳ Not Started (Capture Addon Refactor)
- [ ] Introduce `CaptureConfig` usage
- [ ] Output `CapturedRequest` objects
- [ ] Remove file writes
- [ ] Make URL filtering configurable

### Phase 4: ⏳ Not Started (Proxy Layer Decoupling)
- [ ] Inject configs & addon
- [ ] Remove Claude client awareness

### Phase 5: ⏳ Partially Done (Claude Client)
- [x] Dynamic block scrubbing
- [ ] Add subprocess tests
- [ ] Parameterize command inputs

### Phase 6: ⏳ Not Started (App Orchestration)
- [ ] Convert to coordination-only
- [ ] Accept CLI args
- [ ] Handle output writes

### Validation & Finalization
- [ ] New formatter tests green
- [ ] Capture & proxy tests green
- [ ] Claude client tests green
- [ ] Full integration (Docker) still passes (current: passes with updated snapshot)

## Immediate Next Steps (Execution Order)
1. Refactor `prompt_formatter.py` to expose pure `render_prompt_markdown(captured_request) -> str`
2. Add formatter unit tests (mock Jinja2 environment & template)
3. Move markdown file writing to `app.py`
4. Refactor `capture_addon.py` to emit `CapturedRequest` objects using `CaptureConfig`
5. Adapt `mitm_capture.py` to accept `ProxyConfig` & external addon (remove Claude coupling)
6. Add pytest-subprocess tests for `claude_client.py`
7. Simplify `app.py` orchestration & add integration test covering new pipeline
8. Remove legacy code paths & finalize docs

## Notes
- Snapshot was updated after adding scrubbing logic—content now deterministic.
- Further changes to formatter must preserve snapshot unless intentionally updated.