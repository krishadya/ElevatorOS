# ElevatorOS — Independent Review Checklist

Use this checklist for every milestone review. The reviewer must be independent — do not review your own implementation.

## Pre-Review

- [ ] Run `make verify` from the repository root — all checks must pass before review begins
- [ ] Read the milestone requirements, not just the implementer's summary

---

## Correctness

- [ ] All stated milestone requirements are implemented
- [ ] No features from future milestones were added
- [ ] No unrelated refactoring was performed

## Domain Invariants

- [ ] **Floor boundaries**: Elevators cannot move outside their `[min_floor, max_floor]` range
- [ ] **Capacity**: Elevators reject boarding when at capacity
- [ ] **Passenger lifecycle**: State transitions follow `WAITING → RIDING → ARRIVED`
- [ ] **Boarding guards**: Only `WAITING` passengers can board; assignment conflicts are rejected
- [ ] **Discharge guards**: Passengers can only be discharged at their destination floor
- [ ] Invalid operations raise clear errors (not silent no-ops or corrupted state)

## Deterministic Simulation

- [ ] `SimulationClock` is purely tick-based with no wall-clock dependency
- [ ] No source of non-determinism (unseeded randomness, async races, system time)
- [ ] Two runs with identical inputs produce identical outputs

## State Transitions

- [ ] Passenger state transitions are explicit and validated
- [ ] Elevator direction changes are explicit
- [ ] Door state is checked before movement
- [ ] `BOARDING` state is reserved for future milestone (documented, not used)

## Architecture / Coupling

- [ ] **Scheduling separation**: No dispatch/algorithm logic in `Elevator`, `Building`, or `Passenger`
- [ ] Domain models expose clean interfaces (`add_stop`, `remove_stop`, `board_passenger`, `discharge_passenger`)
- [ ] No dependency on FastAPI, frontend, database, or external services in simulation code
- [ ] `Building` does not tightly couple to `Elevator` scheduling internals

## Typing

- [ ] `mypy` reports no errors
- [ ] No unused imports flagged by editor/linter
- [ ] Type annotations are present on all public methods and properties

## Test Coverage

- [ ] All domain invariants have corresponding test cases
- [ ] Edge cases are tested (boundary floors, full capacity, invalid states)
- [ ] Tests verify error messages, not just that errors are raised
- [ ] No test depends on execution order or shared mutable state
- [ ] Test count matches or exceeds the milestone's reported count

## Packaging

- [ ] `pyproject.toml` is well-formed
- [ ] `tests/` is excluded from package distribution
- [ ] Editable install (`pip install -e ".[dev]"`) succeeds
- [ ] No `tests/__init__.py` in the package

## Git Hygiene

- [ ] `.gitignore` covers `__pycache__/`, `.venv/`, `*.egg-info/`, `.pytest_cache/`
- [ ] No compiled bytecode, virtual environments, or IDE config tracked in the repository

## Regressions

- [ ] All previously passing tests still pass
- [ ] No previously enforced invariant was weakened or removed
- [ ] Error messages remain clear and specific

## Future Compatibility

- [ ] Architecture supports adding interchangeable scheduling algorithms without modifying domain models
- [ ] `stops` list is algorithm-agnostic (no hardcoded priority queue or sorting)
- [ ] Passenger assignment model supports dispatch (pre-assignment via `assigned_elevator_id`)
- [ ] Building provides clean passenger and request management for a future simulation runner

---

## Verdict

After completing the checklist, issue exactly one of:

### ✅ APPROVED FOR NEXT MILESTONE

All checks pass. No critical or important issues. The codebase is ready for the next phase of development.

### ❌ FIXES REQUIRED

List each issue with:
- **Severity**: CRITICAL / IMPORTANT / MINOR
- **File**: Exact file path
- **Problem**: What is wrong
- **Fix**: What needs to change

Fixes must be completed and re-reviewed before proceeding.
