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
- **Encapsulates**: All Anthropic URLs, env vars, CLI specifics

### Layer 5: `prompt_formatter.py` - Pure Formatting
**Responsibility**: Data transformation only
- **Input**: Structured prompt data
- **Output**: Formatted markdown string
- **No I/O**: Pure function, no file operations

## TDD Implementation Steps

### Phase 1: Create Core Interfaces & Models
1. **Create `models.py`** with data classes:
   - `CapturedRequest`, `ProxyConfig`, `CaptureConfig`
2. **Write tests first** for each model's validation
3. **Implement models** to pass tests

### Phase 2: Refactor `prompt_formatter.py` (Pure Function)
1. **Write unit tests** using pytest-mock for template loading
2. **Extract pure formatting** from current implementation
3. **Move file I/O** to app coordinator
4. **Mock jinja2.Environment** for isolated testing

### Phase 3: Refactor `capture_addon.py` (Generic Capture)
1. **Write tests** with pytest-mock for mitmproxy flow objects
2. **Remove Anthropic-specific** logic (make configurable)
3. **Mock HTTP flows** to test filtering logic
4. **Return structured data** instead of writing files

### Phase 4: Refactor `mitm_capture.py` (Generic Proxy)
1. **Write tests** using pytest-mock for mitmproxy components
2. **Mock DumpMaster** and proxy lifecycle
3. **Remove Claude client** dependencies
4. **Accept generic addons** and configurations

### Phase 5: Extract `claude_client.py` (Claude-Specific)
1. **Write tests** with **pytest-subprocess** for CLI interactions:
   ```python
   # Mock Claude CLI version check
   fp.register_subprocess(["claude", "-v"], stdout=b"claude 1.0.110")
   
   # Mock actual Claude command execution
   fp.register_subprocess(
       ["claude", "-p", "hello", "--model", "haiku"], 
       stdout=b"Hello! How can I help you today?"
   )
   ```
2. **Mock subprocess.run** calls using pytest-subprocess fixture `fp`
3. **Move all Anthropic URLs/configs** here
4. **Create clean interface** for app coordination

### Phase 6: Simplify `app.py` (Coordination Only)
1. **Write integration tests** with selective mocking
2. **Mock layer boundaries** using pytest-mock
3. **Wire up all layers** through clean interfaces
4. **Handle file I/O** at app level only

## Testing Strategy with pytest-subprocess & pytest-mock
- **pytest-subprocess**: Mock all `subprocess.run()` calls in `claude_client.py`
  - Mock `claude -v` version checks
  - Mock `claude -p hello --model haiku` execution
  - Simulate different exit codes and outputs
- **pytest-mock**: Mock other boundaries
  - `mitmproxy` components for proxy testing
  - File system operations for I/O testing
  - `jinja2.Environment` for template testing
- **Integration tests**: Layer boundaries tested with selective mocking
- **Snapshot tests**: Keep existing Docker integration test
- **Run `uv run pytest`** after each phase

## Dependencies to Add
- Add `pytest-subprocess` to dev dependencies in `pyproject.toml`
- Add `pytest-mock` to dev dependencies in `pyproject.toml`
- Use `fp` fixture for subprocess mocking
- Use `mocker` fixture for other mocking needs

## Benefits of New Architecture
- **Extensible**: Easy to add support for other CLI tools
- **Testable**: Each layer can be unit tested independently
- **Fast tests**: pytest-subprocess eliminates actual CLI execution
- **Maintainable**: Clear separation of concerns
- **Configurable**: Generic components work for any API
- **TDD-driven**: Tests guide the refactoring process
- **Reliable**: No dependency on external Claude CLI during testing

## Implementation Progress

### Phase 1: ✅ Planning Complete
- [x] Architecture design
- [x] TDD strategy defined
- [x] Testing approach with pytest-subprocess

### Phase 2: 🔄 In Progress
- [ ] Add testing dependencies
- [ ] Create models.py with tests
- [ ] Refactor prompt_formatter.py
- [ ] Refactor capture_addon.py
- [ ] Refactor mitm_capture.py
- [ ] Extract claude_client.py
- [ ] Simplify app.py

### Phase 3: ⏳ Validation
- [ ] Run comprehensive tests
- [ ] Verify all layers work together
- [ ] Ensure Docker integration still works