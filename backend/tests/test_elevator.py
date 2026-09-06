"""Tests for the Elevator domain model."""

import pytest

from app.simulation.elevator import Elevator
from app.simulation.enums import Direction, DoorState, ElevatorState, PassengerState
from app.simulation.passenger import Passenger


# ── Creation ─────────────────────────────────────────────────────────


class TestElevatorCreation:
    """Verify valid and invalid elevator construction."""

    def test_valid_creation_defaults(self):
        e = Elevator(id="E1")
        assert e.id == "E1"
        assert e.current_floor == 1
        assert e.direction == Direction.IDLE
        assert e.door_state == DoorState.CLOSED
        assert e.state == ElevatorState.IDLE
        assert e.capacity == 8
        assert e.min_floor == 1
        assert e.max_floor == 10
        assert e.passengers == []
        assert e.stops == []

    def test_valid_creation_custom(self):
        e = Elevator(
            id="E2",
            current_floor=5,
            direction=Direction.UP,
            capacity=12,
            min_floor=0,
            max_floor=20,
        )
        assert e.current_floor == 5
        assert e.capacity == 12
        assert e.min_floor == 0
        assert e.max_floor == 20

    def test_invalid_current_floor_below_min(self):
        with pytest.raises(ValueError, match="current_floor"):
            Elevator(id="E1", current_floor=0, min_floor=1, max_floor=10)

    def test_invalid_current_floor_above_max(self):
        with pytest.raises(ValueError, match="current_floor"):
            Elevator(id="E1", current_floor=11, min_floor=1, max_floor=10)

    def test_invalid_min_greater_than_max(self):
        with pytest.raises(ValueError, match="min_floor"):
            Elevator(id="E1", min_floor=10, max_floor=5)

    def test_invalid_zero_capacity(self):
        with pytest.raises(ValueError, match="capacity"):
            Elevator(id="E1", capacity=0)


# ── Floor bounds & movement ──────────────────────────────────────────


class TestElevatorMovement:
    """Verify movement respects floor boundaries and direction."""

    def test_move_up(self):
        e = Elevator(id="E1", current_floor=1, max_floor=10)
        e.direction = Direction.UP
        assert e.move_one_floor() == 2
        assert e.current_floor == 2

    def test_move_down(self):
        e = Elevator(id="E1", current_floor=5, min_floor=1, max_floor=10)
        e.direction = Direction.DOWN
        assert e.move_one_floor() == 4

    def test_cannot_move_above_max(self):
        e = Elevator(id="E1", current_floor=10, max_floor=10)
        e.direction = Direction.UP
        with pytest.raises(RuntimeError, match="outside bounds"):
            e.move_one_floor()

    def test_cannot_move_below_min(self):
        e = Elevator(id="E1", current_floor=1, min_floor=1, max_floor=10)
        e.direction = Direction.DOWN
        with pytest.raises(RuntimeError, match="outside bounds"):
            e.move_one_floor()

    def test_cannot_move_when_idle(self):
        e = Elevator(id="E1", direction=Direction.IDLE)
        with pytest.raises(RuntimeError, match="IDLE"):
            e.move_one_floor()

    def test_cannot_move_with_doors_open(self):
        e = Elevator(id="E1", direction=Direction.UP, door_state=DoorState.OPEN)
        with pytest.raises(RuntimeError, match="OPEN"):
            e.move_one_floor()


# ── Stop management ──────────────────────────────────────────────────


class TestElevatorStops:
    """Verify stop add/remove behaviour."""

    def test_add_valid_stop(self):
        e = Elevator(id="E1", min_floor=1, max_floor=10)
        e.add_stop(5)
        assert 5 in e.stops

    def test_add_duplicate_stop_preserves_duplicates(self):
        e = Elevator(id="E1", min_floor=1, max_floor=10)
        e.add_stop(5)
        e.add_stop(5)
        assert e.stops.count(5) == 2

    def test_add_stop_outside_range_raises(self):
        e = Elevator(id="E1", min_floor=1, max_floor=10)
        with pytest.raises(ValueError, match="outside"):
            e.add_stop(11)

    def test_remove_stop(self):
        e = Elevator(id="E1", min_floor=1, max_floor=10)
        e.add_stop(5)
        e.remove_stop(5)
        assert 5 not in e.stops

    def test_remove_nonexistent_stop_is_noop(self):
        e = Elevator(id="E1")
        e.remove_stop(99)  # should not raise

    def test_add_stop_allows_intentional_duplicates(self):
        """Routes like [5, 2, 5] must be preserved in order."""
        e = Elevator(id="E1", min_floor=1, max_floor=10)
        e.add_stop(5)
        e.add_stop(2)
        e.add_stop(5)
        assert e.stops == [5, 2, 5]

    def test_insert_stop_preserves_existing_route_order(self):
        e = Elevator(id="E1", min_floor=1, max_floor=10)
        e.add_stop(5)
        e.add_stop(9)

        e.insert_stop(1, 7)

        assert e.stops == [5, 7, 9]


# ── Passenger boarding & discharge ───────────────────────────────────


class TestElevatorPassengers:
    """Verify capacity enforcement, boarding, and discharge.

    All boarding/discharge tests use door_state=DoorState.OPEN because
    Milestone 2 enforces that doors must be open for passenger exchange.
    """

    def _make_passenger(self, pid: str, origin: int, dest: int) -> Passenger:
        return Passenger(id=pid, origin_floor=origin, destination_floor=dest)

    def test_board_passenger(self):
        e = Elevator(
            id="E1", current_floor=3, capacity=2,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=3, dest=7)
        e.board_passenger(p, current_tick=10)

        assert e.passenger_count == 1
        assert p.state == PassengerState.RIDING
        assert p.pickup_time == 10
        assert p.assigned_elevator_id == "E1"

    def test_board_passenger_wrong_floor_raises(self):
        e = Elevator(
            id="E1", current_floor=3, min_floor=1,
            max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=5, dest=7)
        with pytest.raises(RuntimeError, match="floor"):
            e.board_passenger(p, current_tick=0)

    def test_capacity_enforcement(self):
        e = Elevator(
            id="E1", current_floor=1, capacity=2,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p1 = self._make_passenger("P1", origin=1, dest=5)
        p2 = self._make_passenger("P2", origin=1, dest=6)
        p3 = self._make_passenger("P3", origin=1, dest=7)

        e.board_passenger(p1, current_tick=0)
        e.board_passenger(p2, current_tick=0)

        assert not e.can_board()
        with pytest.raises(RuntimeError, match="capacity"):
            e.board_passenger(p3, current_tick=0)

    def test_discharge_passenger(self):
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        e.board_passenger(p, current_tick=0)

        # Close doors, move to destination, then open doors
        e.close_doors()
        e.finish_closing()
        e.direction = Direction.UP
        for _ in range(4):  # floor 1 -> 5
            e.move_one_floor()
        e.open_doors()
        e.finish_opening()

        discharged = e.discharge_passenger("P1", current_tick=10)

        assert discharged.id == "P1"
        assert discharged.state == PassengerState.ARRIVED
        assert discharged.dropoff_time == 10
        assert e.passenger_count == 0

    def test_discharge_nonexistent_passenger_raises(self):
        e = Elevator(id="E1", door_state=DoorState.OPEN)
        with pytest.raises(ValueError, match="not in elevator"):
            e.discharge_passenger("GHOST", current_tick=0)

    def test_can_board_reflects_capacity(self):
        e = Elevator(
            id="E1", current_floor=1, capacity=1,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        assert e.can_board()
        p = self._make_passenger("P1", origin=1, dest=5)
        e.board_passenger(p, current_tick=0)
        assert not e.can_board()


# ── Boarding & discharge invariants (review fixes) ───────────────────


class TestElevatorBoardingInvariants:
    """Verify boarding guards added during review fix pass."""

    def _make_passenger(self, pid: str, origin: int, dest: int) -> Passenger:
        return Passenger(id=pid, origin_floor=origin, destination_floor=dest)

    def test_board_passenger_not_waiting_raises(self):
        """A passenger who is not WAITING cannot board."""
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        p.state = PassengerState.ARRIVED  # invalid state for boarding
        with pytest.raises(RuntimeError, match="WAITING"):
            e.board_passenger(p, current_tick=0)

    def test_board_passenger_already_riding_raises(self):
        """A RIDING passenger cannot board again."""
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        p.state = PassengerState.RIDING
        with pytest.raises(RuntimeError, match="WAITING"):
            e.board_passenger(p, current_tick=0)

    def test_board_passenger_assigned_to_other_elevator_raises(self):
        """A passenger pre-assigned to another elevator cannot board this one."""
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        p.assigned_elevator_id = "E2"
        with pytest.raises(RuntimeError, match="assigned to elevator"):
            e.board_passenger(p, current_tick=0)

    def test_board_passenger_assigned_to_same_elevator_ok(self):
        """A passenger pre-assigned to this elevator can board normally."""
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        p.assigned_elevator_id = "E1"
        e.board_passenger(p, current_tick=0)
        assert p.state == PassengerState.RIDING
        assert p.assigned_elevator_id == "E1"

    def test_board_passenger_unassigned_gets_assigned(self):
        """A passenger with no assignment gets assigned on boarding."""
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        assert p.assigned_elevator_id is None
        e.board_passenger(p, current_tick=0)
        assert p.assigned_elevator_id == "E1"

    def test_board_passenger_doors_closed_raises(self):
        """Cannot board when doors are CLOSED."""
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.CLOSED,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        with pytest.raises(RuntimeError, match="CLOSED"):
            e.board_passenger(p, current_tick=0)

    def test_discharge_doors_closed_raises(self):
        """Cannot discharge when doors are CLOSED."""
        e = Elevator(
            id="E1", current_floor=5, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.state = PassengerState.RIDING
        p.assigned_elevator_id = "E1"
        e.passengers.append(p)

        # Close the doors
        e.close_doors()
        e.finish_closing()

        with pytest.raises(RuntimeError, match="CLOSED"):
            e.discharge_passenger("P1", current_tick=10)


class TestElevatorDischargeInvariants:
    """Verify discharge destination-floor guard added during review fix."""

    def _make_passenger(self, pid: str, origin: int, dest: int) -> Passenger:
        return Passenger(id=pid, origin_floor=origin, destination_floor=dest)

    def test_discharge_at_wrong_floor_raises(self):
        """Cannot discharge a passenger before reaching their destination."""
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        e.board_passenger(p, current_tick=0)
        # Elevator is still at floor 1, destination is 5
        with pytest.raises(RuntimeError, match="destination"):
            e.discharge_passenger("P1", current_tick=5)

    def test_discharge_at_correct_floor_works(self):
        """Discharge succeeds when elevator is at the destination floor."""
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        e.board_passenger(p, current_tick=0)

        # Close doors, move to destination, reopen
        e.close_doors()
        e.finish_closing()
        e.direction = Direction.UP
        for _ in range(4):
            e.move_one_floor()
        e.open_doors()
        e.finish_opening()

        discharged = e.discharge_passenger("P1", current_tick=10)
        assert discharged.state == PassengerState.ARRIVED
        assert discharged.dropoff_time == 10
        assert e.passenger_count == 0


# ── Door state machine ───────────────────────────────────────────────


class TestElevatorDoorStateMachine:
    """Verify door state transitions enforce valid sequence."""

    def test_full_door_cycle(self):
        """CLOSED → OPENING → OPEN → CLOSING → CLOSED."""
        e = Elevator(id="E1")
        assert e.door_state == DoorState.CLOSED

        e.open_doors()
        assert e.door_state == DoorState.OPENING

        e.finish_opening()
        assert e.door_state == DoorState.OPEN

        e.close_doors()
        assert e.door_state == DoorState.CLOSING

        e.finish_closing()
        assert e.door_state == DoorState.CLOSED

    def test_open_doors_requires_closed(self):
        e = Elevator(id="E1", door_state=DoorState.OPEN)
        with pytest.raises(RuntimeError, match="expected CLOSED"):
            e.open_doors()

    def test_finish_opening_requires_opening(self):
        e = Elevator(id="E1", door_state=DoorState.CLOSED)
        with pytest.raises(RuntimeError, match="expected OPENING"):
            e.finish_opening()

    def test_close_doors_requires_open(self):
        e = Elevator(id="E1", door_state=DoorState.CLOSED)
        with pytest.raises(RuntimeError, match="expected OPEN"):
            e.close_doors()

    def test_finish_closing_requires_closing(self):
        e = Elevator(id="E1", door_state=DoorState.OPEN)
        with pytest.raises(RuntimeError, match="expected CLOSING"):
            e.finish_closing()

    def test_cannot_move_during_opening(self):
        e = Elevator(id="E1", direction=Direction.UP)
        e.open_doors()
        with pytest.raises(RuntimeError, match="OPENING"):
            e.move_one_floor()

    def test_cannot_move_during_closing(self):
        e = Elevator(id="E1", door_state=DoorState.OPEN, direction=Direction.UP)
        e.close_doors()
        with pytest.raises(RuntimeError, match="CLOSING"):
            e.move_one_floor()


# ── Two-phase boarding ───────────────────────────────────────────────


class TestElevatorTwoPhaseBoarding:
    """Verify begin_boarding / finish_boarding flow."""

    def _make_passenger(self, pid: str, origin: int, dest: int) -> Passenger:
        return Passenger(id=pid, origin_floor=origin, destination_floor=dest)

    def test_begin_boarding_sets_boarding_state(self):
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        e.begin_boarding(p, current_tick=10)

        assert p.state == PassengerState.BOARDING
        assert p.pickup_time == 10
        assert p.assigned_elevator_id == "E1"
        assert p in e.passengers

    def test_finish_boarding_sets_riding_state(self):
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        e.begin_boarding(p, current_tick=10)
        e.finish_boarding(p)

        assert p.state == PassengerState.RIDING

    def test_finish_boarding_requires_boarding_state(self):
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        e.board_passenger(p, current_tick=10)  # goes straight to RIDING
        with pytest.raises(RuntimeError, match="expected BOARDING"):
            e.finish_boarding(p)

    def test_begin_boarding_requires_open_doors(self):
        e = Elevator(
            id="E1", current_floor=1, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.CLOSED,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        with pytest.raises(RuntimeError, match="CLOSED"):
            e.begin_boarding(p, current_tick=0)


# ── Bulk discharge ───────────────────────────────────────────────────


class TestElevatorBulkDischarge:
    """Verify discharge_passengers_at_destination (all-at-once)."""

    def _make_passenger(self, pid: str, origin: int, dest: int) -> Passenger:
        return Passenger(id=pid, origin_floor=origin, destination_floor=dest)

    def test_discharge_all_at_destination(self):
        e = Elevator(
            id="E1", current_floor=5, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p1 = self._make_passenger("P1", origin=1, dest=5)
        p2 = self._make_passenger("P2", origin=2, dest=5)
        p3 = self._make_passenger("P3", origin=1, dest=8)

        for p in [p1, p2, p3]:
            p.state = PassengerState.RIDING
            p.assigned_elevator_id = "E1"
            e.passengers.append(p)

        discharged = e.discharge_passengers_at_destination(current_tick=20)

        assert len(discharged) == 2
        assert all(p.state == PassengerState.ARRIVED for p in discharged)
        assert all(p.dropoff_time == 20 for p in discharged)
        assert e.passenger_count == 1
        assert e.passengers[0].id == "P3"

    def test_discharge_none_when_no_match(self):
        e = Elevator(
            id="E1", current_floor=3, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.OPEN,
        )
        p = self._make_passenger("P1", origin=1, dest=5)
        p.state = PassengerState.RIDING
        p.assigned_elevator_id = "E1"
        e.passengers.append(p)

        discharged = e.discharge_passengers_at_destination(current_tick=10)
        assert len(discharged) == 0
        assert e.passenger_count == 1

    def test_discharge_requires_open_doors(self):
        e = Elevator(
            id="E1", current_floor=5, capacity=8,
            min_floor=1, max_floor=10, door_state=DoorState.CLOSED,
        )
        with pytest.raises(RuntimeError, match="CLOSED"):
            e.discharge_passengers_at_destination(current_tick=10)
