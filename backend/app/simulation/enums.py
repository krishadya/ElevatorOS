"""Enums and state types for the ElevatorOS simulation."""

from enum import Enum, auto


class Direction(Enum):
    """Direction of travel for an elevator or passenger."""

    UP = auto()
    DOWN = auto()
    IDLE = auto()


class DoorState(Enum):
    """Current state of an elevator's doors."""

    OPEN = auto()
    CLOSED = auto()
    OPENING = auto()
    CLOSING = auto()


class PassengerState(Enum):
    """Lifecycle state of a passenger within the simulation.

    Transitions:
        WAITING -> BOARDING -> RIDING -> ARRIVED
        WAITING -> ABANDONED  (if passenger gives up, future feature)
    """

    WAITING = auto()
    BOARDING = auto()
    RIDING = auto()
    ARRIVED = auto()
    ABANDONED = auto()
