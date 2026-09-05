"""Elevator hall-call request model for ElevatorOS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.simulation.enums import Direction


@dataclass
class ElevatorRequest:
    """A hall-call request generated when a passenger presses an elevator button.

    Attributes:
        id: Unique request identifier.
        origin_floor: Floor where the request was made.
        direction: Requested travel direction.
        timestamp: Simulation tick when the request was created.
        passenger_id: ID of the passenger who made the request.
        assigned_elevator_id: ID of the elevator assigned to serve this
            request (None until a dispatch algorithm assigns one).
    """

    id: str
    origin_floor: int
    direction: Direction
    timestamp: int
    passenger_id: str
    assigned_elevator_id: Optional[str] = None

    @property
    def is_assigned(self) -> bool:
        """Whether a dispatch algorithm has assigned an elevator."""
        return self.assigned_elevator_id is not None
