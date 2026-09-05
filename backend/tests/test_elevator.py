"""Tests for the Elevator domain model."""

import pytest

from app.simulation.elevator import Elevator
from app.simulation.enums import Direction, DoorState, PassengerState
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

    def test_add_duplicate_stop_is_idempotent(self):
        e = Elevator(id="E1", min_floor=1, max_floor=10)
        e.add_stop(5)
        e.add_stop(5)
        assert e.stops.count(5) == 1

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


# ── Passenger boarding & discharge ───────────────────────────────────


class TestElevatorPassengers:
    """Verify capacity enforcement, boarding, and discharge."""

    def _make_passenger(self, pid: str, origin: int, dest: int) -> Passenger:
        return Passenger(id=pid, origin_floor=origin, destination_floor=dest)

    def test_board_passenger(self):
        e = Elevator(id="E1", current_floor=3, capacity=2, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=3, dest=7)
        e.board_passenger(p, current_tick=10)

        assert e.passenger_count == 1
        assert p.state == PassengerState.RIDING
        assert p.pickup_time == 10
        assert p.assigned_elevator_id == "E1"

    def test_board_passenger_wrong_floor_raises(self):
        e = Elevator(id="E1", current_floor=3, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=5, dest=7)
        with pytest.raises(RuntimeError, match="floor"):
            e.board_passenger(p, current_tick=0)

    def test_capacity_enforcement(self):
        e = Elevator(id="E1", current_floor=1, capacity=2, min_floor=1, max_floor=10)
        p1 = self._make_passenger("P1", origin=1, dest=5)
        p2 = self._make_passenger("P2", origin=1, dest=6)
        p3 = self._make_passenger("P3", origin=1, dest=7)

        e.board_passenger(p1, current_tick=0)
        e.board_passenger(p2, current_tick=0)

        assert not e.can_board()
        with pytest.raises(RuntimeError, match="capacity"):
            e.board_passenger(p3, current_tick=0)

    def test_discharge_passenger(self):
        e = Elevator(id="E1", current_floor=1, capacity=8, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=1, dest=5)
        e.board_passenger(p, current_tick=0)

        # Move elevator to the passenger's destination floor
        e.direction = Direction.UP
        for _ in range(4):  # floor 1 -> 5
            e.move_one_floor()

        discharged = e.discharge_passenger("P1", current_tick=10)

        assert discharged.id == "P1"
        assert discharged.state == PassengerState.ARRIVED
        assert discharged.dropoff_time == 10
        assert e.passenger_count == 0

    def test_discharge_nonexistent_passenger_raises(self):
        e = Elevator(id="E1")
        with pytest.raises(ValueError, match="not in elevator"):
            e.discharge_passenger("GHOST", current_tick=0)

    def test_can_board_reflects_capacity(self):
        e = Elevator(id="E1", current_floor=1, capacity=1, min_floor=1, max_floor=10)
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
        e = Elevator(id="E1", current_floor=1, capacity=8, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=1, dest=5)
        p.state = PassengerState.ARRIVED  # invalid state for boarding
        with pytest.raises(RuntimeError, match="WAITING"):
            e.board_passenger(p, current_tick=0)

    def test_board_passenger_already_riding_raises(self):
        """A RIDING passenger cannot board again."""
        e = Elevator(id="E1", current_floor=1, capacity=8, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=1, dest=5)
        p.state = PassengerState.RIDING
        with pytest.raises(RuntimeError, match="WAITING"):
            e.board_passenger(p, current_tick=0)

    def test_board_passenger_assigned_to_other_elevator_raises(self):
        """A passenger pre-assigned to another elevator cannot board this one."""
        e = Elevator(id="E1", current_floor=1, capacity=8, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=1, dest=5)
        p.assigned_elevator_id = "E2"
        with pytest.raises(RuntimeError, match="assigned to elevator"):
            e.board_passenger(p, current_tick=0)

    def test_board_passenger_assigned_to_same_elevator_ok(self):
        """A passenger pre-assigned to this elevator can board normally."""
        e = Elevator(id="E1", current_floor=1, capacity=8, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=1, dest=5)
        p.assigned_elevator_id = "E1"
        e.board_passenger(p, current_tick=0)
        assert p.state == PassengerState.RIDING
        assert p.assigned_elevator_id == "E1"

    def test_board_passenger_unassigned_gets_assigned(self):
        """A passenger with no assignment gets assigned on boarding."""
        e = Elevator(id="E1", current_floor=1, capacity=8, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=1, dest=5)
        assert p.assigned_elevator_id is None
        e.board_passenger(p, current_tick=0)
        assert p.assigned_elevator_id == "E1"


class TestElevatorDischargeInvariants:
    """Verify discharge destination-floor guard added during review fix."""

    def _make_passenger(self, pid: str, origin: int, dest: int) -> Passenger:
        return Passenger(id=pid, origin_floor=origin, destination_floor=dest)

    def test_discharge_at_wrong_floor_raises(self):
        """Cannot discharge a passenger before reaching their destination."""
        e = Elevator(id="E1", current_floor=1, capacity=8, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=1, dest=5)
        e.board_passenger(p, current_tick=0)
        # Elevator is still at floor 1, destination is 5
        with pytest.raises(RuntimeError, match="destination"):
            e.discharge_passenger("P1", current_tick=5)

    def test_discharge_at_correct_floor_works(self):
        """Discharge succeeds when elevator is at the destination floor."""
        e = Elevator(id="E1", current_floor=1, capacity=8, min_floor=1, max_floor=10)
        p = self._make_passenger("P1", origin=1, dest=5)
        e.board_passenger(p, current_tick=0)

        # Move to destination
        e.direction = Direction.UP
        for _ in range(4):
            e.move_one_floor()

        discharged = e.discharge_passenger("P1", current_tick=10)
        assert discharged.state == PassengerState.ARRIVED
        assert discharged.dropoff_time == 10
        assert e.passenger_count == 0

