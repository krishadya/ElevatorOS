"""Tests for the Passenger domain model."""

import pytest

from app.simulation.enums import Direction, PassengerState
from app.simulation.passenger import Passenger


class TestPassengerCreation:
    """Verify valid and invalid passenger construction."""

    def test_valid_creation(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5, arrival_time=0)
        assert p.id == "P1"
        assert p.origin_floor == 1
        assert p.destination_floor == 5
        assert p.state == PassengerState.WAITING
        assert p.pickup_time is None
        assert p.dropoff_time is None
        assert p.assigned_elevator_id is None

    def test_origin_equals_destination_raises(self):
        with pytest.raises(ValueError, match="must differ"):
            Passenger(id="P1", origin_floor=3, destination_floor=3)


class TestPassengerDirection:
    """Verify direction is correctly derived from origin/destination."""

    def test_going_up(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        assert p.direction == Direction.UP

    def test_going_down(self):
        p = Passenger(id="P1", origin_floor=8, destination_floor=2)
        assert p.direction == Direction.DOWN


class TestPassengerTimings:
    """Verify wait_time, ride_time, and total_time calculations."""

    def test_wait_time_none_before_pickup(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5, arrival_time=10)
        assert p.wait_time is None

    def test_wait_time_after_pickup(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5, arrival_time=10)
        p.pickup_time = 25
        assert p.wait_time == 15

    def test_ride_time_after_dropoff(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5, arrival_time=0)
        p.pickup_time = 10
        p.dropoff_time = 30
        assert p.ride_time == 20

    def test_total_time_after_dropoff(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5, arrival_time=5)
        p.pickup_time = 10
        p.dropoff_time = 30
        assert p.total_time == 25

    def test_total_time_none_before_dropoff(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5, arrival_time=5)
        p.pickup_time = 10
        assert p.total_time is None


class TestPassengerState:
    """Verify passenger lifecycle state transitions."""

    def test_default_state_is_waiting(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        assert p.state == PassengerState.WAITING

    def test_state_can_be_set_to_boarding(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.state = PassengerState.BOARDING
        assert p.state == PassengerState.BOARDING

    def test_state_can_be_set_to_arrived(self):
        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.state = PassengerState.ARRIVED
        assert p.state == PassengerState.ARRIVED
