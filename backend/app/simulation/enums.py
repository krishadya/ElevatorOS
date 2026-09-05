"""Enums and state types for the ElevatorOS simulation."""

from enum import Enum, auto


class Direction(Enum):
    """Direction of travel for an elevator or passenger."""

    UP = auto()
    DOWN = auto()
    IDLE = auto()


class DoorState(Enum):
    """Current state of an elevator's doors.

    Valid transitions (enforced by the Elevator model):
        CLOSED → OPENING → OPEN → CLOSING → CLOSED
    """

    OPEN = auto()
    CLOSED = auto()
    OPENING = auto()
    CLOSING = auto()


class ElevatorState(Enum):
    """High-level operating mode of an elevator.

    Distinct from Direction (spatial) and DoorState (mechanical).
    Used by the simulation engine to drive the per-tick lifecycle.

    States:
        IDLE:    No stops queued, doors closed, stationary.
        MOVING:  Traveling between floors (doors closed).
        STOPPED: At a stop, processing door/passenger lifecycle.
    """

    IDLE = auto()
    MOVING = auto()
    STOPPED = auto()


class PassengerState(Enum):
    """Lifecycle state of a passenger within the simulation.

    Transitions:
        WAITING -> BOARDING -> RIDING -> ARRIVED
        WAITING -> ABANDONED  (if passenger gives up, future feature)

    BOARDING is a real state in Milestone 2: passengers spend one tick
    per person transitioning from WAITING to RIDING while the elevator
    doors are OPEN.
    """

    WAITING = auto()
    BOARDING = auto()
    RIDING = auto()
    ARRIVED = auto()
    ABANDONED = auto()


class EventType(Enum):
    """Types of events emitted by the simulation engine.

    Events are lightweight, framework-free data. No pub/sub or
    external dependencies. The engine collects them in a list;
    consumers read them after the fact.
    """

    ELEVATOR_DEPARTED = auto()
    ELEVATOR_MOVED = auto()
    ELEVATOR_STOPPED = auto()
    ELEVATOR_IDLE = auto()
    DOORS_OPENING = auto()
    DOORS_OPEN = auto()
    DOORS_CLOSING = auto()
    DOORS_CLOSED = auto()
    PASSENGER_BOARDING = auto()
    PASSENGER_BOARDED = auto()
    PASSENGER_DISCHARGED = auto()
