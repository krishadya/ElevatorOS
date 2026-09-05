"""Passenger domain model for ElevatorOS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.simulation.enums import Direction, PassengerState


@dataclass
class Passenger:
    """A person requesting elevator service.

    Attributes:
        id: Unique passenger identifier.
        origin_floor: Floor where the passenger is waiting.
        destination_floor: Floor the passenger wants to reach.
        arrival_time: Simulation tick when the passenger appeared.
        pickup_time: Simulation tick when the passenger boarded (None until boarded).
        dropoff_time: Simulation tick when the passenger arrived (None until arrived).
        assigned_elevator_id: ID of the elevator serving this passenger (None until assigned).
        state: Current lifecycle state.
    """

    id: str
    origin_floor: int
    destination_floor: int
    arrival_time: int = 0
    pickup_time: Optional[int] = None
    dropoff_time: Optional[int] = None
    assigned_elevator_id: Optional[str] = None
    state: PassengerState = PassengerState.WAITING

    def __post_init__(self) -> None:
        if self.origin_floor == self.destination_floor:
            raise ValueError(
                f"origin_floor and destination_floor must differ, "
                f"both are {self.origin_floor}"
            )

    @property
    def direction(self) -> Direction:
        """Derive travel direction from origin and destination."""
        if self.destination_floor > self.origin_floor:
            return Direction.UP
        return Direction.DOWN

    @property
    def wait_time(self) -> Optional[int]:
        """Ticks between arrival and pickup, or None if not yet picked up."""
        if self.pickup_time is None:
            return None
        return self.pickup_time - self.arrival_time

    @property
    def ride_time(self) -> Optional[int]:
        """Ticks between pickup and dropoff, or None if not yet dropped off."""
        if self.pickup_time is None or self.dropoff_time is None:
            return None
        return self.dropoff_time - self.pickup_time

    @property
    def total_time(self) -> Optional[int]:
        """Ticks between arrival and dropoff, or None if not yet dropped off."""
        if self.dropoff_time is None:
            return None
        return self.dropoff_time - self.arrival_time
