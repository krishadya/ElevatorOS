"""Tests for the Nearest Suitable Car dispatch algorithm.

Covers: direction matching, tier priority, idle fallback, distance
ties, ID tie-breaking, all-away scenario, assignment consistency,
assign-once, deterministic replay, and FCFS regression guard.
"""

from __future__ import annotations

from app.algorithms.fcfs import FCFSDispatch
from app.algorithms.nearest_car import NearestSuitableCarDispatch
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


def _make_elevator(
    eid: str,
    current_floor: int = 1,
    direction: Direction = Direction.IDLE,
) -> Elevator:
    """Create a test elevator on floors 1–10."""
    return Elevator(
        id=eid,
        current_floor=current_floor,
        direction=direction,
        min_floor=1,
        max_floor=10,
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestMatchingDirectionBeatsCloser:
    """Tier 1 (matching direction) beats a physically closer car."""

    def test_matching_direction_beats_closer_wrong_direction(self) -> None:
        """E1 going UP from floor 4 beats E2 going DOWN from floor 5
        for a Floor 6 UP call, even though E2 is closer."""
        p1 = _make_passenger("P1", origin=6, destination=9)
        r1 = _make_request(
            "R1", origin=6, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )

        e1 = _make_elevator("E1", current_floor=4, direction=Direction.UP)
        e2 = _make_elevator("E2", current_floor=5, direction=Direction.DOWN)

        algo = NearestSuitableCarDispatch()
        results = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1, e2],
            passengers={"P1": p1},
        )

        assert len(results) == 1
        assert results[0].elevator_id == "E1"


class TestUpCallPrefersCarBelowMovingUp:
    """UP call prefers an elevator below the caller moving UP."""

    def test_up_call_prefers_car_below_moving_up(self) -> None:
        """Floor 6 UP: E1 at floor 3 going UP (Tier 1) beats
        E2 at floor 9 going DOWN (Tier 3, moving toward but wrong dir)."""
        p1 = _make_passenger("P1", origin=6, destination=10)
        r1 = _make_request(
            "R1", origin=6, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )

        e1 = _make_elevator("E1", current_floor=3, direction=Direction.UP)
        e2 = _make_elevator("E2", current_floor=9, direction=Direction.DOWN)

        algo = NearestSuitableCarDispatch()
        results = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1, e2],
            passengers={"P1": p1},
        )

        assert results[0].elevator_id == "E1"


class TestDownCallPrefersCarAboveMovingDown:
    """DOWN call prefers an elevator above the caller moving DOWN."""

    def test_down_call_prefers_car_above_moving_down(self) -> None:
        """Floor 6 DOWN: E2 at floor 9 going DOWN (Tier 1) beats
        E1 at floor 4 going UP (Tier 4, moving away)."""
        p1 = _make_passenger("P1", origin=6, destination=1)
        r1 = _make_request(
            "R1", origin=6, direction=Direction.DOWN, timestamp=0, passenger_id="P1"
        )

        e1 = _make_elevator("E1", current_floor=4, direction=Direction.UP)
        e2 = _make_elevator("E2", current_floor=9, direction=Direction.DOWN)

        algo = NearestSuitableCarDispatch()
        results = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1, e2],
            passengers={"P1": p1},
        )

        assert results[0].elevator_id == "E2"


class TestIdleElevatorFallback:
    """When no Tier 1 match exists, picks an IDLE elevator (Tier 2)."""

    def test_idle_elevator_fallback(self) -> None:
        """Floor 5 UP: E1 going DOWN from floor 8 (Tier 3, toward but
        wrong dir) loses to E2 IDLE at floor 7 (Tier 2)."""
        p1 = _make_passenger("P1", origin=5, destination=8)
        r1 = _make_request(
            "R1", origin=5, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )

        e1 = _make_elevator("E1", current_floor=8, direction=Direction.DOWN)
        e2 = _make_elevator("E2", current_floor=7, direction=Direction.IDLE)

        algo = NearestSuitableCarDispatch()
        results = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1, e2],
            passengers={"P1": p1},
        )

        assert results[0].elevator_id == "E2"


class TestDistanceTieWithinSameTier:
    """Same tier → closer car wins."""

    def test_distance_tie_within_same_tier(self) -> None:
        """Floor 5 UP: both E1 (floor 3) and E2 (floor 2) are going UP
        (both Tier 1). E1 is closer (distance 2 vs 3)."""
        p1 = _make_passenger("P1", origin=5, destination=8)
        r1 = _make_request(
            "R1", origin=5, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )

        e1 = _make_elevator("E1", current_floor=3, direction=Direction.UP)
        e2 = _make_elevator("E2", current_floor=2, direction=Direction.UP)

        algo = NearestSuitableCarDispatch()
        results = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1, e2],
            passengers={"P1": p1},
        )

        assert results[0].elevator_id == "E1"


class TestElevatorIdTiebreak:
    """Same tier, same distance → lower ID wins."""

    def test_elevator_id_tiebreak(self) -> None:
        """Floor 5 UP: E1 and E2 are both IDLE at floor 5 (Tier 2,
        distance 0). E1 wins by ID."""
        p1 = _make_passenger("P1", origin=5, destination=8)
        r1 = _make_request(
            "R1", origin=5, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )

        e1 = _make_elevator("E1", current_floor=5, direction=Direction.IDLE)
        e2 = _make_elevator("E2", current_floor=5, direction=Direction.IDLE)

        algo = NearestSuitableCarDispatch()
        results = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1, e2],
            passengers={"P1": p1},
        )

        assert results[0].elevator_id == "E1"


class TestAllElevatorsMovingAway:
    """When all elevators are Tier 4, picks the closest among them."""

    def test_all_elevators_moving_away(self) -> None:
        """Floor 5 UP: E1 at floor 8 going UP (away, distance 3),
        E2 at floor 2 going DOWN (away, distance 3),
        E3 at floor 3 going DOWN (away, distance 2).
        E3 is closest among Tier 4."""
        p1 = _make_passenger("P1", origin=5, destination=9)
        r1 = _make_request(
            "R1", origin=5, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )

        e1 = _make_elevator("E1", current_floor=8, direction=Direction.UP)
        e2 = _make_elevator("E2", current_floor=2, direction=Direction.DOWN)
        e3 = _make_elevator("E3", current_floor=3, direction=Direction.DOWN)

        algo = NearestSuitableCarDispatch()
        results = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1, e2, e3],
            passengers={"P1": p1},
        )

        assert results[0].elevator_id == "E3"


class TestPassengerRequestAssignmentConsistency:
    """Both passenger and request get the correct assigned_elevator_id."""

    def test_passenger_request_assignment_consistency(self) -> None:
        """After dispatch, passenger and request agree on which elevator."""
        p1 = _make_passenger("P1", origin=3, destination=7)
        r1 = _make_request(
            "R1", origin=3, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )
        e1 = _make_elevator("E1", current_floor=1, direction=Direction.UP)

        algo = NearestSuitableCarDispatch()
        results = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1],
            passengers={"P1": p1},
        )

        assert len(results) == 1
        assert r1.assigned_elevator_id == "E1"
        assert p1.assigned_elevator_id == "E1"
        # Pickup and destination added to stops
        assert e1.stops == [3, 7]


class TestRequestAssignedOnlyOnce:
    """Running dispatch twice on the same request produces no new results."""

    def test_request_assigned_only_once(self) -> None:
        p1 = _make_passenger("P1", origin=4, destination=8)
        r1 = _make_request(
            "R1", origin=4, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )
        e1 = _make_elevator("E1", current_floor=2, direction=Direction.UP)

        algo = NearestSuitableCarDispatch()

        results1 = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1],
            passengers={"P1": p1},
        )
        assert len(results1) == 1
        assert r1.is_assigned

        results2 = algo.dispatch(
            pending_requests=[r1],
            elevators=[e1],
            passengers={"P1": p1},
        )
        assert len(results2) == 0


class TestDeterministicReplay:
    """Two identical runs produce identical results."""

    def test_deterministic_replay(self) -> None:
        def run_dispatch() -> tuple[list[str], list[list[int]]]:
            p1 = _make_passenger("P1", origin=3, destination=8)
            p2 = _make_passenger("P2", origin=7, destination=2)
            p3 = _make_passenger("P3", origin=5, destination=9)

            requests = [
                _make_request("R1", origin=3, direction=Direction.UP, timestamp=0, passenger_id="P1"),
                _make_request("R2", origin=7, direction=Direction.DOWN, timestamp=0, passenger_id="P2"),
                _make_request("R3", origin=5, direction=Direction.UP, timestamp=1, passenger_id="P3"),
            ]

            e1 = _make_elevator("E1", current_floor=1, direction=Direction.UP)
            e2 = _make_elevator("E2", current_floor=10, direction=Direction.DOWN)

            algo = NearestSuitableCarDispatch()
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


class TestFCFSStillWorks:
    """FCFS behavior is completely unchanged (regression guard)."""

    def test_fcfs_still_works(self) -> None:
        """FCFS ignores direction and uses fewest-stops. Verify it still
        does that even now that NearestSuitableCar exists."""
        p1 = _make_passenger("P1", origin=6, destination=9)
        p2 = _make_passenger("P2", origin=3, destination=7)

        r1 = _make_request(
            "R1", origin=6, direction=Direction.UP, timestamp=0, passenger_id="P1"
        )
        r2 = _make_request(
            "R2", origin=3, direction=Direction.UP, timestamp=1, passenger_id="P2"
        )

        # E1 going DOWN, E2 going UP. FCFS doesn't care — uses fewest stops.
        e1 = _make_elevator("E1", current_floor=8, direction=Direction.DOWN)
        e2 = _make_elevator("E2", current_floor=2, direction=Direction.UP)

        fcfs = FCFSDispatch()
        results = fcfs.dispatch(
            pending_requests=[r1, r2],
            elevators=[e1, e2],
            passengers={"P1": p1, "P2": p2},
        )

        assert len(results) == 2
        # FCFS: R1 → E1 (both 0 stops, E1 < E2 by ID)
        assert results[0].request_id == "R1"
        assert results[0].elevator_id == "E1"
        # FCFS: R2 → E2 (E1 now has 2 stops, E2 has 0)
        assert results[1].request_id == "R2"
        assert results[1].elevator_id == "E2"
