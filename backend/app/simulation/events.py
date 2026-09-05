"""Lightweight simulation event representation for ElevatorOS.

Events are plain frozen dataclasses — no pub/sub, no callbacks,
no external dependencies. The engine collects them in a list;
consumers (future analytics, replay, logging) read them after
the simulation runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.simulation.enums import EventType


@dataclass(frozen=True)
class SimulationEvent:
    """A single event emitted during a simulation tick.

    Attributes:
        tick: The simulation tick when this event occurred.
        event_type: The kind of event (see EventType enum).
        elevator_id: ID of the elevator involved.
        floor: Floor where the event occurred (if applicable).
        passenger_id: ID of the passenger involved (if applicable).
        details: Optional human-readable description.
    """

    tick: int
    event_type: EventType
    elevator_id: str
    floor: int | None = None
    passenger_id: str | None = None
    details: str = ""
