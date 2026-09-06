"""Building domain model for ElevatorOS.

The Building is the top-level container for a simulation scenario.
It holds elevators, waiting passengers, and active requests, and
validates that all components are consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.simulation.elevator import Elevator
from app.simulation.passenger import Passenger
from app.simulation.request import ElevatorRequest


@dataclass
class Building:
    """A building containing one or more elevators.

    Attributes:
        num_floors: Total number of floors (e.g., 10 means floors 1–10).
        min_floor: Lowest floor number (default 1).
        elevators: List of elevators in the building.
        waiting_passengers: Passengers waiting in hallways for pickup.
        active_requests: Hall-call requests that have not yet been fully served.
    """

    num_floors: int
    min_floor: int = 1
    elevators: list[Elevator] = field(default_factory=list)
    waiting_passengers: list[Passenger] = field(default_factory=list)
    active_requests: list[ElevatorRequest] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.num_floors < 1:
            raise ValueError(
                f"num_floors must be >= 1, got {self.num_floors}"
            )
        # Validate every elevator fits within the building
        for elev in self.elevators:
            if elev.min_floor < self.min_floor:
                raise ValueError(
                    f"Elevator {elev.id} min_floor ({elev.min_floor}) is below "
                    f"building min_floor ({self.min_floor})"
                )
            if elev.max_floor > self.max_floor:
                raise ValueError(
                    f"Elevator {elev.id} max_floor ({elev.max_floor}) exceeds "
                    f"building max_floor ({self.max_floor})"
                )

    @property
    def max_floor(self) -> int:
        """Highest floor number in the building."""
        return self.min_floor + self.num_floors - 1

    @property
    def floor_range(self) -> range:
        """Range of valid floor numbers (inclusive)."""
        return range(self.min_floor, self.max_floor + 1)

    # ── Factory ──────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        num_floors: int,
        num_elevators: int,
        elevator_capacity: int = 8,
        min_floor: int = 1,
    ) -> Building:
        """Convenience factory to build a standard building.

        Creates ``num_elevators`` identical elevators that serve all
        floors in the building.

        Args:
            num_floors: Total number of floors.
            num_elevators: Number of elevators to create.
            elevator_capacity: Passenger capacity per elevator.
            min_floor: Lowest floor number.

        Returns:
            A fully configured Building instance.
        """
        max_floor = min_floor + num_floors - 1
        elevators = [
            Elevator(
                id=f"E{i + 1}",
                current_floor=min_floor,
                capacity=elevator_capacity,
                min_floor=min_floor,
                max_floor=max_floor,
            )
            for i in range(num_elevators)
        ]
        return cls(
            num_floors=num_floors,
            min_floor=min_floor,
            elevators=elevators,
        )

    # ── Queries ──────────────────────────────────────────────────────

    def is_valid_floor(self, floor: int) -> bool:
        """Check whether a floor number is within the building's range."""
        return floor in self.floor_range

    def get_elevator(self, elevator_id: str) -> Optional[Elevator]:
        """Find an elevator by its ID, or None if not found."""
        for elev in self.elevators:
            if elev.id == elevator_id:
                return elev
        return None

    # ── Passenger management ─────────────────────────────────────────

    def add_waiting_passenger(self, passenger: Passenger) -> None:
        """Register a new passenger waiting in the hallway.

        Raises:
            ValueError: If the passenger's origin or destination floor
                is outside the building.
        """
        if not self.is_valid_floor(passenger.origin_floor):
            raise ValueError(
                f"Passenger {passenger.id} origin floor {passenger.origin_floor} "
                f"is outside building range [{self.min_floor}, {self.max_floor}]"
            )
        if not self.is_valid_floor(passenger.destination_floor):
            raise ValueError(
                f"Passenger {passenger.id} destination floor {passenger.destination_floor} "
                f"is outside building range [{self.min_floor}, {self.max_floor}]"
            )
        self.waiting_passengers.append(passenger)

    def add_request(self, request: ElevatorRequest) -> None:
        """Register a new hall-call request.

        Raises:
            ValueError: If the request's origin floor is outside the building.
        """
        if not self.is_valid_floor(request.origin_floor):
            raise ValueError(
                f"Request {request.id} origin floor {request.origin_floor} "
                f"is outside building range [{self.min_floor}, {self.max_floor}]"
            )
        self.active_requests.append(request)

    def remove_serviced_requests(
        self, elevator_id: str, floor: int
    ) -> list[ElevatorRequest]:
        """Remove hall calls served when an assigned elevator opens at a floor.

        A hall call is served at pickup: its assigned elevator has reached the
        origin floor and opened its doors. The remaining active requests keep
        their original order for deterministic behavior.
        """
        serviced: list[ElevatorRequest] = []
        remaining: list[ElevatorRequest] = []
        for request in self.active_requests:
            if (
                request.assigned_elevator_id == elevator_id
                and request.origin_floor == floor
            ):
                serviced.append(request)
            else:
                remaining.append(request)
        self.active_requests = remaining
        return serviced

    def remove_waiting_passenger(self, passenger_id: str) -> Passenger:
        """Remove a passenger from the waiting list (e.g. when they board).

        Args:
            passenger_id: ID of the passenger to remove.

        Returns:
            The removed Passenger object.

        Raises:
            ValueError: If the passenger is not in the waiting list.
        """
        for i, p in enumerate(self.waiting_passengers):
            if p.id == passenger_id:
                return self.waiting_passengers.pop(i)

        raise ValueError(
            f"Passenger {passenger_id} is not in the waiting list."
        )
