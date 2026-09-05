"""Deterministic timing constants for the ElevatorOS simulation.

All durations are expressed in simulation ticks, not wall-clock time.
Changing these values alters simulation pacing but preserves determinism.
Future milestones may make these configurable per-building or per-elevator.
"""

# ── Door state machine timing ────────────────────────────────────────

DOOR_OPENING_TICKS: int = 1
"""Ticks for doors to transition from CLOSED → OPEN (via OPENING)."""

DOOR_CLOSING_TICKS: int = 1
"""Ticks for doors to transition from OPEN → CLOSED (via CLOSING)."""

DOOR_OPEN_DWELL_TICKS: int = 2
"""Minimum ticks doors remain OPEN for passenger exchange.

The engine keeps doors open for at least this many ticks. If passengers
are still boarding (1 per tick), the dwell extends automatically.
"""

# ── Passenger throughput ─────────────────────────────────────────────

PASSENGERS_BOARDING_PER_TICK: int = 1
"""Number of passengers that can board per tick while doors are OPEN.

Discharge is all-at-once when doors open at the destination floor.
"""
