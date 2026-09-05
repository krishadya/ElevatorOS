"""Elevator domain model for ElevatorOS.

The Elevator manages its own physical state (floor, doors, passengers)
but does NOT contain scheduling/dispatch logic. Algorithms set stops
externally via ``add_stop()``; the elevator simply services them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.simulation.enums import Direction, DoorState, PassengerState
from app.simulation.passenger import Passenger


@dataclass
class Elevator:
    """A single elevator car within a building.

    Attributes:
        id: Unique elevator identifier.
        current_floor: The floor the elevator is currently on.
        direction: Current travel direction (UP, DOWN, or IDLE).
        door_state: Current state of the elevator doors.
        capacity: Maximum number of passengers the elevator can hold.
        min_floor: Lowest floor this elevator can visit.
        max_floor: Highest floor this elevator can visit.
        passengers: List of passengers currently inside the car.
        stops: Ordered list of floors the elevator will visit.
            Managed externally by dispatch algorithms via add_stop/remove_stop.
    """

    id: str
    current_floor: int = 1
    direction: Direction = Direction.IDLE
    door_state: DoorState = DoorState.CLOSED
    capacity: int = 8
    min_floor: int = 1
    max_floor: int = 10
    passengers: list[Passenger] = field(default_factory=list)
    stops: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.min_floor > self.max_floor:
            raise ValueError(
                f"min_floor ({self.min_floor}) must be <= max_floor ({self.max_floor})"
            )
        if not (self.min_floor <= self.current_floor <= self.max_floor):
            raise ValueError(
                f"current_floor ({self.current_floor}) must be between "
                f"min_floor ({self.min_floor}) and max_floor ({self.max_floor})"
            )
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")

    # ── Stop management ──────────────────────────────────────────────

    def add_stop(self, floor: int) -> None:
        """Add a floor to the stop list if it's valid and not already queued.

        Raises:
            ValueError: If the floor is outside this elevator's range.
        """
        self._validate_floor(floor)
        if floor not in self.stops:
            self.stops.append(floor)

    def remove_stop(self, floor: int) -> None:
        """Remove a floor from the stop list (no-op if not present)."""
        if floor in self.stops:
            self.stops.remove(floor)

    # ── Movement ─────────────────────────────────────────────────────

    def move_one_floor(self) -> int:
        """Move the elevator one floor in its current direction.

        Returns:
            The new current_floor after moving.

        Raises:
            RuntimeError: If the elevator is IDLE (no direction to move).
            RuntimeError: If moving would exceed floor boundaries.
        """
        if self.direction == Direction.IDLE:
            raise RuntimeError("Cannot move an IDLE elevator. Set direction first.")

        if self.door_state != DoorState.CLOSED:
            raise RuntimeError(
                f"Cannot move while doors are {self.door_state.name}. "
                f"Close doors first."
            )

        next_floor = (
            self.current_floor + 1
            if self.direction == Direction.UP
            else self.current_floor - 1
        )

        if not (self.min_floor <= next_floor <= self.max_floor):
            raise RuntimeError(
                f"Cannot move {self.direction.name} from floor {self.current_floor}: "
                f"floor {next_floor} is outside bounds [{self.min_floor}, {self.max_floor}]"
            )

        self.current_floor = next_floor
        return self.current_floor

    # ── Passenger handling ───────────────────────────────────────────

    @property
    def passenger_count(self) -> int:
        """Number of passengers currently in the elevator."""
        return len(self.passengers)

    def can_board(self) -> bool:
        """Whether the elevator has room for at least one more passenger."""
        return self.passenger_count < self.capacity

    def board_passenger(self, passenger: Passenger, current_tick: int) -> None:
        """Board a passenger into the elevator (atomic for Milestone 1).

        Boarding is treated as instantaneous in Milestone 1. The
        ``PassengerState.BOARDING`` state is reserved for Milestone 2,
        which will model time-based door and boarding transitions.

        Args:
            passenger: The passenger to board.
            current_tick: The current simulation tick (for recording pickup time).

        Raises:
            RuntimeError: If the elevator is at capacity.
            RuntimeError: If the passenger is not on the elevator's current floor.
            RuntimeError: If the passenger is not in WAITING state.
            RuntimeError: If the passenger is assigned to a different elevator.
        """
        if passenger.state != PassengerState.WAITING:
            raise RuntimeError(
                f"Passenger {passenger.id} is in state {passenger.state.name}, "
                f"expected WAITING."
            )
        if not self.can_board():
            raise RuntimeError(
                f"Elevator {self.id} is at capacity ({self.capacity}). "
                f"Cannot board passenger {passenger.id}."
            )
        if passenger.origin_floor != self.current_floor:
            raise RuntimeError(
                f"Passenger {passenger.id} is on floor {passenger.origin_floor}, "
                f"but elevator {self.id} is on floor {self.current_floor}."
            )
        if (
            passenger.assigned_elevator_id is not None
            and passenger.assigned_elevator_id != self.id
        ):
            raise RuntimeError(
                f"Passenger {passenger.id} is assigned to elevator "
                f"{passenger.assigned_elevator_id}, not {self.id}."
            )

        passenger.state = PassengerState.RIDING
        passenger.pickup_time = current_tick
        passenger.assigned_elevator_id = self.id
        self.passengers.append(passenger)

    def discharge_passenger(self, passenger_id: str, current_tick: int) -> Passenger:
        """Remove a passenger from the elevator at their destination floor.

        Args:
            passenger_id: ID of the passenger to discharge.
            current_tick: The current simulation tick (for recording dropoff time).

        Returns:
            The discharged Passenger object.

        Raises:
            ValueError: If the passenger is not in this elevator.
            RuntimeError: If the elevator is not at the passenger's
                destination floor.
        """
        for i, p in enumerate(self.passengers):
            if p.id == passenger_id:
                if self.current_floor != p.destination_floor:
                    raise RuntimeError(
                        f"Cannot discharge passenger {passenger_id} at floor "
                        f"{self.current_floor}: destination is floor "
                        f"{p.destination_floor}."
                    )
                passenger = self.passengers.pop(i)
                passenger.state = PassengerState.ARRIVED
                passenger.dropoff_time = current_tick
                return passenger

        raise ValueError(
            f"Passenger {passenger_id} is not in elevator {self.id}."
        )

    # ── Internals ────────────────────────────────────────────────────

    def _validate_floor(self, floor: int) -> None:
        """Raise ValueError if floor is outside this elevator's bounds."""
        if not (self.min_floor <= floor <= self.max_floor):
            raise ValueError(
                f"Floor {floor} is outside elevator {self.id}'s range "
                f"[{self.min_floor}, {self.max_floor}]"
            )
