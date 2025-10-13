# Refactor tests

## Context

- Test suite structure under `tests/` diverges from the conceptual layout of `src/claudit`, making it harder to spot coverage gaps and follow dependencies.
- Multiple Claude Code strategy tests duplicate setup for captured requests, commands, and prompt content, which increases maintenance cost when behavior changes.

## Goals

- Mirror the `src/claudit` package structure in `tests/` so that module ownership is obvious.
- Consolidate shared fixtures or builders for Claude Code strategy tests to eliminate repeated JSON payload scaffolding.
- Remove `TestClaudeCodeStrategyCommand` once equivalent coverage exists through higher value scenarios.

## Non Goals

- No changes to runtime behavior of the agents or strategies beyond what is required to keep tests passing.
- No redesign of snapshot tooling or mitm proxy capture logic unless blocked by the refactor.

## Implementation Plan

- Inventory current modules under `src/claudit` and map them to desired test module locations.
- Define the target directory layout (for example: `tests/claudit/agents/claude_code/`) and identify any integration style tests that should remain top level.
- Extract common Claude Code fixtures into a shared module or `conftest.py`, covering captured requests, prompt payloads, and command specs.
- Relocate existing tests to the new layout, updating imports and snapshot paths as needed.
- Delete the low value `TestClaudeCodeStrategyCommand` class once command coverage is exercised elsewhere.
- Run `mise test-all` after restructuring to ensure no regressions.

## Decisions

- Keep tests that exercise Claude Code behavior under `tests/agents/`, regardless of integration vs unit scope, so related logic stays co-located.
- Continue storing syrupy snapshots in the shared `tests/__snapshots__/` directory after files move.
- Design the new layout so adding additional agent strategies has an obvious home (`tests/claudit/agents/<agent_name>`).

## Progress Log

- 2024-07-11: Established goals, constraints, and high level plan; no code changes yet.
- 2024-07-11: Captured decisions on test placement, snapshot directory usage, and future agent namespace expectations.
