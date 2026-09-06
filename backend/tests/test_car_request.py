"""Tests for Hall Call vs Car Request separation.

Hall Calls (ElevatorRequest):
    - Dispatched by algorithms (FCFS, Nearest Suitable Car)
    - Contain floor + direction
    - Must be assigned to an elevator

Car Requests (CarRequest):
    - Bypass dispatch entirely
    - Go directly to a named elevator's stop list
    - Validated against elevator ID and floor bounds
"""

from __future__ import annotations

import pytest

from app.algorithms.fcfs import FCFSDispatch
from app.algorithms.nearest_car import NearestSuitableCarDispatch
from app.simulation.building import Building
from app.simulation.car_request import CarRequest, process_car_request
from app.simulation.elevator import Elevator
from app.simulation.enums import Direction, ElevatorState
from app.simulation.passenger import Passenger
from app.simulation.request import ElevatorRequest


# ── Helpers ──────────────────────────────────────────────────────────


def _make_passenger(
    pid: str, origin: int, destination: int, arrival: int = 0
) -> Passenger:
    return Passenger(
        id=pid,
        origin_floor=origin,
        destination_floor=destination,
        arrival_time=arrival,
    )


def _make_hall_call(
    rid: str,
    origin: int,
    direction: Direction,
    timestamp: int,
    passenger_id: str,
) -> ElevatorRequest:
    return ElevatorRequest(
        id=rid,
        origin_floor=origin,
        direction=direction,
        timestamp=timestamp,
        passenger_id=passenger_id,
    )


def _make_elevator(
    eid: str,
    current_floor: int = 1,
    direction: Direction = Direction.IDLE,
    min_floor: int = 1,
    max_floor: int = 10,
) -> Elevator:
    return Elevator(
        id=eid,
        current_floor=current_floor,
        direction=direction,
        min_floor=min_floor,
        max_floor=max_floor,
    )


# ── Hall Call Tests ──────────────────────────────────────────────────


class TestHallCallUp:
    """UP hall call dispatched through FCFS."""

    def test_hall_call_up_dispatched(self) -> None:
        """An UP hall call is assigned to an elevator by FCFS."""
        p1 = _make_passenger("P1", origin=3, destination=7)
        hc = _make_hall_call(
            "HC1", origin=3, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )
        elevator = _make_elevator("E1")
        algo = FCFSDispatch()

        results = algo.dispatch(
            pending_requests=[hc],
            elevators=[elevator],
            passengers={"P1": p1},
        )

        assert len(results) == 1
        assert results[0].elevator_id == "E1"
        assert hc.assigned_elevator_id == "E1"
        assert p1.assigned_elevator_id == "E1"
        assert elevator.stops == [3]


class TestHallCallDown:
    """DOWN hall call dispatched through Nearest Suitable Car."""

    def test_hall_call_down_dispatched(self) -> None:
        """A DOWN hall call is assigned using direction-aware dispatch."""
        p1 = _make_passenger("P1", origin=7, destination=2)
        hc = _make_hall_call(
            "HC1", origin=7, direction=Direction.DOWN, timestamp=0, passenger_id="P1"
        )
        e1 = _make_elevator("E1", current_floor=3, direction=Direction.UP)
        e2 = _make_elevator("E2", current_floor=9, direction=Direction.DOWN)
        algo = NearestSuitableCarDispatch()

        results = algo.dispatch(
            pending_requests=[hc],
            elevators=[e1, e2],
            passengers={"P1": p1},
        )

        assert len(results) == 1
        # E2 is Tier 1 (above caller, going DOWN = matching direction)
        assert results[0].elevator_id == "E2"
        assert hc.assigned_elevator_id == "E2"


class TestHallCallCannotBeAssignedTwice:
    """A hall call that is already assigned is skipped on re-dispatch."""

    def test_hall_call_cannot_be_assigned_twice(self) -> None:
        p1 = _make_passenger("P1", origin=5, destination=8)
        hc = _make_hall_call(
            "HC1", origin=5, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )
        elevator = _make_elevator("E1")
        algo = FCFSDispatch()

        results1 = algo.dispatch(
            pending_requests=[hc],
            elevators=[elevator],
            passengers={"P1": p1},
        )
        assert len(results1) == 1

        results2 = algo.dispatch(
            pending_requests=[hc],
            elevators=[elevator],
            passengers={"P1": p1},
        )
        assert len(results2) == 0


# ── Car Request Tests ────────────────────────────────────────────────


class TestCarRequestAddsDestination:
    """Car request adds destination to the correct elevator only."""

    def test_car_request_adds_destination_to_correct_elevator(self) -> None:
        """Floor is appended to the named elevator's stops."""
        building = Building.create(num_floors=10, num_elevators=2)

        cr = CarRequest(id="CR1", elevator_id="E2", destination_floor=7, timestamp=0)
        process_car_request(cr, building)

        e1 = building.get_elevator("E1")
        e2 = building.get_elevator("E2")
        assert e1 is not None and e2 is not None
        assert e1.stops == []  # E1 untouched
        assert e2.stops == [7]  # Only E2 gets the stop


class TestCarRequestNoDispatch:
    """Car requests bypass dispatch algorithms entirely."""

    def test_car_request_no_dispatch_involved(self) -> None:
        """process_car_request works without any algorithm instance."""
        building = Building.create(num_floors=10, num_elevators=1)

        cr = CarRequest(id="CR1", elevator_id="E1", destination_floor=5, timestamp=0)
        # No dispatch algorithm needed — just call process_car_request
        process_car_request(cr, building)

        e1 = building.get_elevator("E1")
        assert e1 is not None
        assert e1.stops == [5]


class TestCarRequestInvalidElevatorId:
    """Invalid elevator ID raises a clear error."""

    def test_car_request_invalid_elevator_id(self) -> None:
        building = Building.create(num_floors=10, num_elevators=1)

        cr = CarRequest(
            id="CR1", elevator_id="NONEXISTENT", destination_floor=5, timestamp=0
        )
        with pytest.raises(ValueError, match="not found"):
            process_car_request(cr, building)


class TestCarRequestInvalidFloor:
    """Invalid destination floor raises a clear error."""

    def test_car_request_invalid_floor(self) -> None:
        building = Building.create(num_floors=10, num_elevators=1)

        cr = CarRequest(
            id="CR1", elevator_id="E1", destination_floor=99, timestamp=0
        )
        with pytest.raises(ValueError, match="outside"):
            process_car_request(cr, building)


class TestCarRequestRepeatedDestination:
    """Pressing the same floor twice adds it twice deterministically."""

    def test_car_request_repeated_destination_deterministic(self) -> None:
        """Duplicate stops are allowed (engine handles them correctly)."""
        building = Building.create(num_floors=10, num_elevators=1)

        cr1 = CarRequest(id="CR1", elevator_id="E1", destination_floor=5, timestamp=0)
        cr2 = CarRequest(id="CR2", elevator_id="E1", destination_floor=5, timestamp=1)
        process_car_request(cr1, building)
        process_car_request(cr2, building)

        e1 = building.get_elevator("E1")
        assert e1 is not None
        assert e1.stops == [5, 5]


class TestCarRequestWithExistingStops:
    """Car request appends without corrupting existing route."""

    def test_car_request_with_existing_stops(self) -> None:
        building = Building.create(num_floors=10, num_elevators=1)
        e1 = building.get_elevator("E1")
        assert e1 is not None
        e1.add_stop(3)
        e1.add_stop(6)

        cr = CarRequest(id="CR1", elevator_id="E1", destination_floor=9, timestamp=0)
        process_car_request(cr, building)

        assert e1.stops == [3, 6, 9]


class TestCarRequestWhileElevatorStopped:
    """Car request works when elevator has STOPPED state."""

    def test_car_request_while_elevator_stopped(self) -> None:
        """Even if the elevator is mid-stop with doors open, a car
        request can still append a destination floor."""
        building = Building.create(num_floors=10, num_elevators=1)
        e1 = building.get_elevator("E1")
        assert e1 is not None
        e1.state = ElevatorState.STOPPED

        cr = CarRequest(id="CR1", elevator_id="E1", destination_floor=8, timestamp=0)
        process_car_request(cr, building)

        assert e1.stops == [8]


class TestCarRequestDeterministicReplay:
    """Two identical runs produce identical results."""

    def test_deterministic_replay(self) -> None:
        def run() -> list[list[int]]:
            building = Building.create(num_floors=10, num_elevators=2)

            requests = [
                CarRequest(id="CR1", elevator_id="E1", destination_floor=5, timestamp=0),
                CarRequest(id="CR2", elevator_id="E2", destination_floor=3, timestamp=0),
                CarRequest(id="CR3", elevator_id="E1", destination_floor=8, timestamp=1),
            ]
            for cr in requests:
                process_car_request(cr, building)

            e1 = building.get_elevator("E1")
            e2 = building.get_elevator("E2")
            assert e1 is not None and e2 is not None
            return [list(e1.stops), list(e2.stops)]

        routes_a = run()
        routes_b = run()
        assert routes_a == routes_b
