# ElevatorOS — Project Rules

## Project Identity

ElevatorOS is a **deterministic multi-elevator dispatch simulation and algorithm benchmarking platform**.

All work must preserve this identity. Do not add unrelated features.

## Architecture Rules

- **Backend simulation logic must remain independent of FastAPI, frontend, WebSockets, and databases.** Domain models are pure Python dataclasses with no framework dependencies.
- **Scheduling algorithms must be interchangeable.** No algorithm logic may be embedded inside `Elevator`, `Building`, `Passenger`, or other domain models. Algorithms operate externally via public methods like `add_stop()` and `remove_stop()`.
- **Domain models enforce physical invariants.** Elevators respect floor boundaries and capacity. Passengers follow a strict lifecycle (`WAITING → RIDING → ARRIVED`). The simulation must reject physically impossible operations with clear errors.
- **Deterministic simulation behavior is non-negotiable.** The `SimulationClock` is purely tick-based with no wall-clock dependency. Two simulation runs with the same inputs must produce identical outputs.

## Scope Rules

- **Work only within the requested milestone scope.** Do not start the next milestone unless explicitly asked.
- **Do not refactor unrelated code.** If a change is not required by the current task, do not make it.
- **Do not add features, dependencies, or infrastructure not explicitly requested.**

## Quality Rules

- **Every behavioral change requires tests.** New invariants, new methods, and new models must all have corresponding test coverage.
- **Preserve deterministic simulation behavior.** Any change that could introduce non-determinism (wall-clock time, random without seed, async races) must be flagged and rejected.
- **Run project verification before claiming completion.** Use `make verify` from the repository root.
- **Do not claim completion with failing tests, lint errors, type-checking errors, or packaging issues.**

## Completion Rules

- **Summarize all modified files at the end of every task.**
- **Report verification results** (pytest count, mypy status, packaging status).
- **Flag any open questions or known limitations** rather than silently ignoring them.
