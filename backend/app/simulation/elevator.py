"""Elevator domain model for ElevatorOS.

The Elevator manages its own physical state (floor, doors, passengers)
but does NOT contain scheduling/dispatch logic. Algorithms set stops
externally via ``add_stop()``; the elevator simply services them.

Door state machine (enforced here):
    CLOSED → OPENING → OPEN → CLOSING → CLOSED

The simulation engine drives the transitions; the elevator enforces
that only valid transitions occur.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.simulation.enums import (
    Direction,
    DoorState,
    ElevatorState,
    PassengerState,
)
from app.simulation.passenger import Passenger


@dataclass
class Elevator:
    """A single elevator car within a building.

    Attributes:
        id: Unique elevator identifier.
        current_floor: The floor the elevator is currently on.
        direction: Current travel direction (UP, DOWN, or IDLE).
        door_state: Current state of the elevator doors.
        state: High-level operating mode (IDLE, MOVING, STOPPED).
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
    state: ElevatorState = ElevatorState.IDLE
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
        """Add a floor to the stop list.

        Duplicate floors are allowed to support routes like [5, 2, 5].
        Floor validation is always enforced.

        Raises:
            ValueError: If the floor is outside this elevator's range.
        """
        self._validate_floor(floor)
        self.stops.append(floor)

    def insert_stop(self, index: int, floor: int) -> None:
        """Insert a validated floor at an explicit route position.

        Route ordering remains the responsibility of the caller (typically a
        dispatch algorithm). This method only validates the floor and
        preserves the existing stops around the insertion point.

        Raises:
            ValueError: If the floor is outside this elevator's range.
            IndexError: If index is not a valid insertion position.
        """
        self._validate_floor(floor)
        if not 0 <= index <= len(self.stops):
            raise IndexError(
                f"Stop insertion index {index} is outside route bounds "
                f"[0, {len(self.stops)}]"
            )
        self.stops.insert(index, floor)

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
            RuntimeError: If doors are not CLOSED.
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

    # ── Door state machine ───────────────────────────────────────────

    def open_doors(self) -> None:
        """Begin opening the doors (CLOSED → OPENING).

        Raises:
            RuntimeError: If doors are not CLOSED.
        """
        if self.door_state != DoorState.CLOSED:
            raise RuntimeError(
                f"Cannot open doors: current state is {self.door_state.name}, "
                f"expected CLOSED."
            )
        self.door_state = DoorState.OPENING

    def finish_opening(self) -> None:
        """Complete door opening (OPENING → OPEN).

        Raises:
            RuntimeError: If doors are not OPENING.
        """
        if self.door_state != DoorState.OPENING:
            raise RuntimeError(
                f"Cannot finish opening: current state is {self.door_state.name}, "
                f"expected OPENING."
            )
        self.door_state = DoorState.OPEN

    def close_doors(self) -> None:
        """Begin closing the doors (OPEN → CLOSING).

        Raises:
            RuntimeError: If doors are not OPEN.
        """
        if self.door_state != DoorState.OPEN:
            raise RuntimeError(
                f"Cannot close doors: current state is {self.door_state.name}, "
                f"expected OPEN."
            )
        self.door_state = DoorState.CLOSING

    def finish_closing(self) -> None:
        """Complete door closing (CLOSING → CLOSED).

        Raises:
            RuntimeError: If doors are not CLOSING.
        """
        if self.door_state != DoorState.CLOSING:
            raise RuntimeError(
                f"Cannot finish closing: current state is {self.door_state.name}, "
                f"expected CLOSING."
            )
        self.door_state = DoorState.CLOSED

    # ── Passenger handling ───────────────────────────────────────────

    @property
    def passenger_count(self) -> int:
        """Number of passengers currently in the elevator."""
        return len(self.passengers)

    def can_board(self) -> bool:
        """Whether the elevator has room for at least one more passenger."""
        return self.passenger_count < self.capacity

    def begin_boarding(self, passenger: Passenger, current_tick: int) -> None:
        """Begin boarding a passenger (WAITING → BOARDING).

        The passenger is validated and their state set to BOARDING.
        They are added to the elevator's passenger list and removed
        from the building's waiting list (by the engine). The engine
        calls ``finish_boarding()`` on the next tick to transition
        them to RIDING.

        Args:
            passenger: The passenger to begin boarding.
            current_tick: The current simulation tick (for recording pickup time).

        Raises:
            RuntimeError: If doors are not OPEN.
            RuntimeError: If the elevator is at capacity.
            RuntimeError: If the passenger is not on the elevator's current floor.
            RuntimeError: If the passenger is not in WAITING state.
            RuntimeError: If the passenger is assigned to a different elevator.
        """
        if self.door_state != DoorState.OPEN:
            raise RuntimeError(
                f"Cannot board: doors are {self.door_state.name}, expected OPEN."
            )
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

        passenger.state = PassengerState.BOARDING
        passenger.pickup_time = current_tick
        passenger.assigned_elevator_id = self.id
        self.passengers.append(passenger)

    def finish_boarding(self, passenger: Passenger) -> None:
        """Complete boarding a passenger (BOARDING → RIDING).

        Args:
            passenger: The passenger who is finishing boarding.

        Raises:
            RuntimeError: If the passenger is not in BOARDING state.
            ValueError: If the passenger is not in this elevator.
        """
        if passenger.state != PassengerState.BOARDING:
            raise RuntimeError(
                f"Passenger {passenger.id} is in state {passenger.state.name}, "
                f"expected BOARDING."
            )
        if passenger not in self.passengers:
            raise ValueError(
                f"Passenger {passenger.id} is not in elevator {self.id}."
            )
        passenger.state = PassengerState.RIDING

    def discharge_passengers_at_destination(self, current_tick: int) -> list[Passenger]:
        """Discharge all passengers whose destination is the current floor.

        All eligible passengers are discharged at once (not 1-per-tick).

        Args:
            current_tick: The current simulation tick (for recording dropoff time).

        Returns:
            List of discharged Passenger objects.

        Raises:
            RuntimeError: If doors are not OPEN.
        """
        if self.door_state != DoorState.OPEN:
            raise RuntimeError(
                f"Cannot discharge: doors are {self.door_state.name}, expected OPEN."
            )

        remaining: list[Passenger] = []
        discharged: list[Passenger] = []
        for p in self.passengers:
            if p.destination_floor == self.current_floor:
                p.state = PassengerState.ARRIVED
                p.dropoff_time = current_tick
                discharged.append(p)
            else:
                remaining.append(p)
        self.passengers = remaining
        return discharged

    # ── Legacy API (Milestone 1 compatibility) ───────────────────────

    def board_passenger(self, passenger: Passenger, current_tick: int) -> None:
        """Atomic board: validates, sets RIDING, and adds to elevator.

        This is the Milestone 1 API preserved for backward compatibility
        and for unit tests that don't need the two-phase boarding flow.
        Requires doors to be OPEN.

        Args:
            passenger: The passenger to board.
            current_tick: The current simulation tick.

        Raises:
            RuntimeError: If doors are not OPEN.
            RuntimeError: If the elevator is at capacity.
            RuntimeError: If the passenger is not on the elevator's current floor.
            RuntimeError: If the passenger is not in WAITING state.
            RuntimeError: If the passenger is assigned to a different elevator.
        """
        if self.door_state != DoorState.OPEN:
            raise RuntimeError(
                f"Cannot board: doors are {self.door_state.name}, expected OPEN."
            )
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
        """Remove a single passenger from the elevator at their destination floor.

        Requires doors to be OPEN.

        Args:
            passenger_id: ID of the passenger to discharge.
            current_tick: The current simulation tick (for recording dropoff time).

        Returns:
            The discharged Passenger object.

        Raises:
            RuntimeError: If doors are not OPEN.
            ValueError: If the passenger is not in this elevator.
            RuntimeError: If the elevator is not at the passenger's
                destination floor.
        """
        if self.door_state != DoorState.OPEN:
            raise RuntimeError(
                f"Cannot discharge: doors are {self.door_state.name}, expected OPEN."
            )
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
