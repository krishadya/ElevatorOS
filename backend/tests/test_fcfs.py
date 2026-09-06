"""Tests for the FCFS (First-Come, First-Served) dispatch algorithm.

Covers: ordering, tie-breaking, single/multi elevator, assignment
correctness, route preservation, edge cases, and deterministic replay.
"""

from __future__ import annotations

import pytest

from app.algorithms.fcfs import FCFSDispatch
from app.simulation.elevator import Elevator
from app.simulation.enums import Direction
from app.simulation.passenger import Passenger
from app.simulation.request import ElevatorRequest


# ── Helpers ──────────────────────────────────────────────────────────


def _make_passenger(
    pid: str, origin: int, destination: int, arrival: int = 0
) -> Passenger:
    """Create a test passenger."""
    return Passenger(
        id=pid,
        origin_floor=origin,
        destination_floor=destination,
        arrival_time=arrival,
    )


def _make_request(
    rid: str,
    origin: int,
    direction: Direction,
    timestamp: int,
    passenger_id: str,
) -> ElevatorRequest:
    """Create a test hall-call request."""
    return ElevatorRequest(
        id=rid,
        origin_floor=origin,
        direction=direction,
        timestamp=timestamp,
        passenger_id=passenger_id,
    )


def _make_elevator(eid: str, current_floor: int = 1) -> Elevator:
    """Create a test elevator on floors 1–10."""
    return Elevator(
        id=eid, current_floor=current_floor, min_floor=1, max_floor=10
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestFCFSOldestFirst:
    """Requests are dispatched in timestamp order (oldest first)."""

    def test_oldest_request_dispatched_first(self) -> None:
        """The request with the earlier timestamp is assigned first."""
        p1 = _make_passenger("P1", origin=3, destination=7)
        p2 = _make_passenger("P2", origin=2, destination=5)

        r1 = _make_request("R1", origin=3, direction=Direction.UP, timestamp=10, passenger_id="P1")
        r2 = _make_request("R2", origin=2, direction=Direction.UP, timestamp=5, passenger_id="P2")

        elevator = _make_elevator("E1")
        algo = FCFSDispatch()

        results = algo.dispatch(
            pending_requests=[r1, r2],  # intentionally out of order
            elevators=[elevator],
            passengers={"P1": p1, "P2": p2},
        )

        assert len(results) == 2
        # R2 (timestamp=5) should be assigned before R1 (timestamp=10)
        assert results[0].request_id == "R2"
        assert results[1].request_id == "R1"


class TestFCFSSameTimestampTieBreaking:
    """Same timestamp → deterministic ordering by request ID."""

    def test_same_timestamp_deterministic_ordering(self) -> None:
        """Requests with the same timestamp are ordered by ID."""
        p1 = _make_passenger("P1", origin=3, destination=7)
        p2 = _make_passenger("P2", origin=2, destination=5)
        p3 = _make_passenger("P3", origin=4, destination=1)

        r_b = _make_request("R-B", origin=3, direction=Direction.UP, timestamp=1, passenger_id="P1")
        r_a = _make_request("R-A", origin=2, direction=Direction.UP, timestamp=1, passenger_id="P2")
        r_c = _make_request("R-C", origin=4, direction=Direction.DOWN, timestamp=1, passenger_id="P3")

        elevator = _make_elevator("E1")
        algo = FCFSDispatch()

        results = algo.dispatch(
            pending_requests=[r_b, r_c, r_a],  # shuffled
            elevators=[elevator],
            passengers={"P1": p1, "P2": p2, "P3": p3},
        )

        assert len(results) == 3
        # Lexicographic: R-A < R-B < R-C
        assert results[0].request_id == "R-A"
        assert results[1].request_id == "R-B"
        assert results[2].request_id == "R-C"


class TestFCFSSingleElevator:
    """All requests go to the sole elevator."""

    def test_single_elevator_all_requests_assigned(self) -> None:
        """With one elevator, every request is assigned to it."""
        passengers = {
            "P1": _make_passenger("P1", origin=1, destination=5),
            "P2": _make_passenger("P2", origin=3, destination=8),
            "P3": _make_passenger("P3", origin=2, destination=6),
        }
        requests = [
            _make_request("R1", origin=1, direction=Direction.UP, timestamp=0, passenger_id="P1"),
            _make_request("R2", origin=3, direction=Direction.UP, timestamp=1, passenger_id="P2"),
            _make_request("R3", origin=2, direction=Direction.UP, timestamp=2, passenger_id="P3"),
        ]
        elevator = _make_elevator("E1")
        algo = FCFSDispatch()

        results = algo.dispatch(
            pending_requests=requests,
            elevators=[elevator],
            passengers=passengers,
        )

        assert len(results) == 3
        assert all(r.elevator_id == "E1" for r in results)


class TestFCFSMultipleElevators:
    """Requests spread across elevators by fewest-stops rule."""

    def test_multiple_elevators_load_balancing(self) -> None:
        """With two elevators, requests alternate (fewest-stops tie-break)."""
        passengers = {
            "P1": _make_passenger("P1", origin=2, destination=5),
            "P2": _make_passenger("P2", origin=3, destination=7),
        }
        requests = [
            _make_request("R1", origin=2, direction=Direction.UP, timestamp=0, passenger_id="P1"),
            _make_request("R2", origin=3, direction=Direction.UP, timestamp=1, passenger_id="P2"),
        ]
        e1 = _make_elevator("E1")
        e2 = _make_elevator("E2")
        algo = FCFSDispatch()

        results = algo.dispatch(
            pending_requests=requests,
            elevators=[e1, e2],
            passengers=passengers,
        )

        assert len(results) == 2
        # R1 → E1 (both start with 0 stops, tie-break: E1 < E2)
        assert results[0].request_id == "R1"
        assert results[0].elevator_id == "E1"
        # R2 → E2 (E1 now has 1 pickup stop, E2 has 0)
        assert results[1].request_id == "R2"
        assert results[1].elevator_id == "E2"


class TestFCFSAssignOnce:
    """A request is never assigned twice."""

    def test_request_assigned_only_once(self) -> None:
        """Running dispatch twice on the same request produces no new results."""
        p1 = _make_passenger("P1", origin=2, destination=5)
        r1 = _make_request("R1", origin=2, direction=Direction.UP, timestamp=0, passenger_id="P1")
        elevator = _make_elevator("E1")
        algo = FCFSDispatch()

        # First dispatch — assigns the request
        results1 = algo.dispatch(
            pending_requests=[r1],
            elevators=[elevator],
            passengers={"P1": p1},
        )
        assert len(results1) == 1
        assert r1.is_assigned

        # Second dispatch — same request is already assigned, skipped
        results2 = algo.dispatch(
            pending_requests=[r1],
            elevators=[elevator],
            passengers={"P1": p1},
        )
        assert len(results2) == 0


class TestFCFSPassengerAssignment:
    """Passenger.assigned_elevator_id is set by dispatch."""

    def test_passenger_assignment_updated(self) -> None:
        """After dispatch, the passenger knows which elevator is coming."""
        p1 = _make_passenger("P1", origin=4, destination=8)
        r1 = _make_request("R1", origin=4, direction=Direction.UP, timestamp=0, passenger_id="P1")
        elevator = _make_elevator("E1")
        algo = FCFSDispatch()

        assert p1.assigned_elevator_id is None

        algo.dispatch(
            pending_requests=[r1],
            elevators=[elevator],
            passengers={"P1": p1},
        )

        assert p1.assigned_elevator_id == "E1"
        assert r1.assigned_elevator_id == "E1"


class TestFCFSStopsAdded:
    """Only the pickup floor is added to the elevator's route by dispatch."""

    def test_pickup_only_added(self) -> None:
        """Dispatch adds origin_floor as a stop; destination is NOT added."""
        p1 = _make_passenger("P1", origin=3, destination=7)
        r1 = _make_request("R1", origin=3, direction=Direction.UP, timestamp=0, passenger_id="P1")
        elevator = _make_elevator("E1")
        algo = FCFSDispatch()

        algo.dispatch(
            pending_requests=[r1],
            elevators=[elevator],
            passengers={"P1": p1},
        )

        assert elevator.stops == [3]

    def test_hall_call_without_passenger_still_appends_pickup(self) -> None:
        """FCFS does not need a destination or Passenger to dispatch a call."""
        request = ElevatorRequest(
            id="R1",
            origin_floor=6,
            direction=Direction.UP,
            timestamp=0,
        )
        elevator = _make_elevator("E1", current_floor=4)
        elevator.direction = Direction.UP
        elevator.add_stop(10)

        results = FCFSDispatch().dispatch(
            pending_requests=[request],
            elevators=[elevator],
        )

        assert results[0].passenger_id is None
        assert request.assigned_elevator_id == "E1"
        assert elevator.stops == [10, 6]


class TestFCFSRoutePreserved:
    """Pre-existing stops are not corrupted by dispatch."""

    def test_existing_route_preserved(self) -> None:
        """Dispatch appends to the route without modifying existing stops."""
        p1 = _make_passenger("P1", origin=4, destination=8)
        r1 = _make_request("R1", origin=4, direction=Direction.UP, timestamp=0, passenger_id="P1")
        elevator = _make_elevator("E1")
        # Pre-load stops: the elevator is already heading to floors 2 and 5
        elevator.add_stop(2)
        elevator.add_stop(5)

        algo = FCFSDispatch()
        algo.dispatch(
            pending_requests=[r1],
            elevators=[elevator],
            passengers={"P1": p1},
        )

        # Existing stops [2, 5] remain in order; pickup floor appended
        assert elevator.stops == [2, 5, 4]


class TestFCFSElevatorAtPickupFloor:
    """Edge case: elevator is already on the passenger's floor."""

    def test_elevator_already_at_pickup_floor(self) -> None:
        """Dispatch still adds the pickup floor as a stop (engine handles it)."""
        p1 = _make_passenger("P1", origin=1, destination=6)
        r1 = _make_request("R1", origin=1, direction=Direction.UP, timestamp=0, passenger_id="P1")
        # Elevator starts on floor 1, same as passenger's origin
        elevator = _make_elevator("E1", current_floor=1)
        algo = FCFSDispatch()

        algo.dispatch(
            pending_requests=[r1],
            elevators=[elevator],
            passengers={"P1": p1},
        )

        assert p1.assigned_elevator_id == "E1"
        # Pickup floor 1 is still added — the engine processes it correctly
        assert elevator.stops == [1]


class TestFCFSDeterministicReplay:
    """Two identical runs produce identical results."""

    def test_deterministic_replay(self) -> None:
        """Running the same inputs twice yields the same assignments and routes."""

        def run_dispatch() -> tuple[list[str], list[list[int]]]:
            p1 = _make_passenger("P1", origin=2, destination=9)
            p2 = _make_passenger("P2", origin=5, destination=1)
            p3 = _make_passenger("P3", origin=3, destination=7)

            requests = [
                _make_request("R1", origin=2, direction=Direction.UP, timestamp=0, passenger_id="P1"),
                _make_request("R2", origin=5, direction=Direction.DOWN, timestamp=0, passenger_id="P2"),
                _make_request("R3", origin=3, direction=Direction.UP, timestamp=1, passenger_id="P3"),
            ]

            e1 = _make_elevator("E1")
            e2 = _make_elevator("E2")
            algo = FCFSDispatch()

            results = algo.dispatch(
                pending_requests=requests,
                elevators=[e1, e2],
                passengers={"P1": p1, "P2": p2, "P3": p3},
            )

            assignment_order = [
                f"{r.request_id}->{r.elevator_id}" for r in results
            ]
            routes = [list(e.stops) for e in [e1, e2]]
            return assignment_order, routes

        assignments_a, routes_a = run_dispatch()
        assignments_b, routes_b = run_dispatch()

        assert assignments_a == assignments_b
        assert routes_a == routes_b
