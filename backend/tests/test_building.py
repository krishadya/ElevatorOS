"""Tests for the Building domain model."""

import pytest

from app.simulation.building import Building
from app.simulation.elevator import Elevator
from app.simulation.enums import Direction
from app.simulation.passenger import Passenger
from app.simulation.request import ElevatorRequest


class TestBuildingCreation:
    """Verify building construction and validation."""

    def test_valid_creation(self):
        b = Building(num_floors=10)
        assert b.num_floors == 10
        assert b.min_floor == 1
        assert b.max_floor == 10
        assert list(b.floor_range) == list(range(1, 11))

    def test_invalid_zero_floors(self):
        with pytest.raises(ValueError, match="num_floors"):
            Building(num_floors=0)

    def test_invalid_negative_floors(self):
        with pytest.raises(ValueError, match="num_floors"):
            Building(num_floors=-5)

    def test_custom_min_floor(self):
        b = Building(num_floors=5, min_floor=0)
        assert b.min_floor == 0
        assert b.max_floor == 4

    def test_factory_create(self):
        b = Building.create(num_floors=10, num_elevators=3, elevator_capacity=6)
        assert len(b.elevators) == 3
        assert all(e.capacity == 6 for e in b.elevators)
        assert all(e.min_floor == 1 for e in b.elevators)
        assert all(e.max_floor == 10 for e in b.elevators)
        # IDs should be E1, E2, E3
        assert [e.id for e in b.elevators] == ["E1", "E2", "E3"]


class TestBuildingElevatorValidation:
    """Verify that elevators must fit within building bounds."""

    def test_elevator_below_building_min(self):
        e = Elevator(id="E1", min_floor=0, max_floor=10, current_floor=0)
        with pytest.raises(ValueError, match="min_floor"):
            Building(num_floors=10, min_floor=1, elevators=[e])

    def test_elevator_above_building_max(self):
        e = Elevator(id="E1", min_floor=1, max_floor=20, current_floor=1)
        with pytest.raises(ValueError, match="max_floor"):
            Building(num_floors=10, min_floor=1, elevators=[e])

    def test_elevator_within_bounds(self):
        e = Elevator(id="E1", min_floor=1, max_floor=10, current_floor=1)
        b = Building(num_floors=10, min_floor=1, elevators=[e])
        assert len(b.elevators) == 1


class TestBuildingFloorValidation:
    """Verify floor validation for passengers and requests."""

    def test_is_valid_floor(self):
        b = Building(num_floors=10, min_floor=1)
        assert b.is_valid_floor(1)
        assert b.is_valid_floor(10)
        assert not b.is_valid_floor(0)
        assert not b.is_valid_floor(11)

    def test_add_passenger_invalid_origin(self):
        b = Building(num_floors=10)
        p = Passenger(id="P1", origin_floor=11, destination_floor=5)
        with pytest.raises(ValueError, match="origin floor"):
            b.add_waiting_passenger(p)

    def test_add_passenger_invalid_destination(self):
        b = Building(num_floors=10)
        p = Passenger(id="P1", origin_floor=5, destination_floor=11)
        with pytest.raises(ValueError, match="destination floor"):
            b.add_waiting_passenger(p)

    def test_add_valid_passenger(self):
        b = Building(num_floors=10)
        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        b.add_waiting_passenger(p)
        assert len(b.waiting_passengers) == 1
        assert b.waiting_passengers[0].id == "P1"

    def test_add_request_invalid_floor(self):
        b = Building(num_floors=10)
        r = ElevatorRequest(
            id="R1", origin_floor=11, direction=Direction.UP,
            timestamp=0, passenger_id="P1"
        )
        with pytest.raises(ValueError, match="origin floor"):
            b.add_request(r)

    def test_add_valid_request(self):
        b = Building(num_floors=10)
        r = ElevatorRequest(
            id="R1", origin_floor=3, direction=Direction.UP,
            timestamp=0, passenger_id="P1"
        )
        b.add_request(r)
        assert len(b.active_requests) == 1


class TestBuildingQueries:
    """Verify helper query methods."""

    def test_get_elevator_found(self):
        b = Building.create(num_floors=10, num_elevators=2)
        assert b.get_elevator("E1") is not None
        assert b.get_elevator("E1").id == "E1"

    def test_get_elevator_not_found(self):
        b = Building.create(num_floors=10, num_elevators=2)
        assert b.get_elevator("E99") is None


class TestBuildingWaitingPassengerRemoval:
    """Verify remove_waiting_passenger behaviour."""

    def test_remove_existing_waiting_passenger(self):
        b = Building(num_floors=10)
        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        b.add_waiting_passenger(p)
        assert len(b.waiting_passengers) == 1

        removed = b.remove_waiting_passenger("P1")
        assert removed.id == "P1"
        assert len(b.waiting_passengers) == 0

    def test_remove_nonexistent_passenger_raises(self):
        b = Building(num_floors=10)
        with pytest.raises(ValueError, match="not in the waiting list"):
            b.remove_waiting_passenger("GHOST")

    def test_remove_from_multiple_passengers(self):
        b = Building(num_floors=10)
        p1 = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p2 = Passenger(id="P2", origin_floor=2, destination_floor=7)
        b.add_waiting_passenger(p1)
        b.add_waiting_passenger(p2)

        removed = b.remove_waiting_passenger("P1")
        assert removed.id == "P1"
        assert len(b.waiting_passengers) == 1
        assert b.waiting_passengers[0].id == "P2"
