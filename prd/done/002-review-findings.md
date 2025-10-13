# Post‑Refactor Implementation Review

## Context
- Scope: Validate that the refactor described in `prd/001-refactor.md` is fully realised in the current codebase.
- Date: 2025-01-18
- Reviewer: Codex (automated agent)

## Executive Summary
The refactor delivers most structural changes, but the implementation diverges from the plan in several critical areas. Prompt selection is incorrect during multi-capture sessions, the agent extensibility story stalls without a registry/factory, and packaging is broken because the generated wheel omits the runtime package.

## Detailed Findings

### 1. Missing Agent Registry / Multi-Agent Wiring
- **Location:** No implementation of `agents/registry.py`; CLI entrypoint (`src/claudit/app.py:60`) instantiates `ClaudeCodeStrategy` directly.
- **Issue:** Plan explicitly called for a registry/factory and sequential execution of all registered agents. Current composition hard-codes a single strategy, so introducing a second agent still requires editing the CLI.
- **Impact:** Refactor objective “support multiple agents via a strategy pattern without touching shared orchestration code” remains unmet; onboarding new agents still couples them to the CLI/App layer.
- **Recommended Fix:** Implement registry/factory, update CLI to resolve strategies via config/flags, and add tests covering selection logic.

## Next Steps
1. Address findings above with targeted patches and tests.
2. Re-run `mise test-all` plus a packaging smoke test (`uv build` or equivalent) after fixes.
3. Update `prd/001-refactor.md` to reflect actual completion status once gaps are closed.

## Appendices
- Reference Plan: `prd/001-refactor.md`
- Review Trigger: Completion claim for refactor plan.
