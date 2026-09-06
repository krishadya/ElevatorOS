"""Nearest Suitable Car dispatch algorithm for ElevatorOS.

A direction-aware algorithm that prefers elevators already heading
toward the caller in the matching direction, rather than blindly
choosing the closest car.

Suitability tiers (best to worst):

    Tier 1 — Elevator is moving toward the call floor AND its
             direction matches the requested direction.
             Example: call is Floor 6 UP, elevator is at Floor 4
             going UP → it will pass Floor 6 while going UP.

    Tier 2 — Elevator is IDLE (stationary, no stops queued).

    Tier 3 — Elevator is moving toward the call floor BUT its
             direction does NOT match the requested direction.
             Example: call is Floor 6 UP, elevator is at Floor 8
             going DOWN → it will reach Floor 6, but going DOWN.

    Tier 4 — Elevator is moving away from the call floor.
             It must finish its current route and reverse before
             it can serve this request.

Within the same tier, ties are broken by:
    1. Smaller distance to the call floor.
    2. Elevator ID (lexicographic) as a final deterministic tie-breaker.

Request processing order: oldest-first by (timestamp, request_id),
same as FCFS.

For a Tier 1 assignment, the pickup floor is inserted before the first
farther stop in the car's current direction. Other suitability tiers retain
append behavior.
"""

from __future__ import annotations

from app.simulation.elevator import Elevator
from app.simulation.enums import Direction
from app.simulation.passenger import Passenger
from app.simulation.request import ElevatorRequest

from app.algorithms.base import DispatchAlgorithm, DispatchResult


def _is_moving_toward(elevator: Elevator, call_floor: int) -> bool:
    """Check whether the elevator is moving toward the call floor.

    An elevator is "moving toward" a floor if:
    - It is going UP and is at or below the call floor, OR
    - It is going DOWN and is at or above the call floor.

    Returns False if the elevator is IDLE (handled separately).
    """
    if elevator.direction == Direction.UP:
        return elevator.current_floor <= call_floor
    if elevator.direction == Direction.DOWN:
        return elevator.current_floor >= call_floor
    return False  # IDLE


def _suitability_key(
    elevator: Elevator,
    call_floor: int,
    call_direction: Direction,
) -> tuple[int, int, str]:
    """Compute the sort key for elevator suitability.

    Returns:
        A tuple of (tier, distance, elevator_id) where lower is better.
    """
    distance = abs(elevator.current_floor - call_floor)

    # Tier 2: IDLE elevator
    if elevator.direction == Direction.IDLE:
        return (2, distance, elevator.id)

    moving_toward = _is_moving_toward(elevator, call_floor)
    direction_matches = elevator.direction == call_direction

    if moving_toward and direction_matches:
        # Tier 1: heading toward caller in the matching direction
        return (1, distance, elevator.id)

    if moving_toward and not direction_matches:
        # Tier 3: heading toward caller but wrong direction
        return (3, distance, elevator.id)

    # Tier 4: moving away from the caller
    return (4, distance, elevator.id)


def _add_pickup_stop(elevator: Elevator, request: ElevatorRequest) -> None:
    """Add a pickup stop, inserting it only when it is on the current path.

    A matching-direction elevator moving toward the call should stop before
    its first farther stop in that direction. All other cases retain simple
    append behavior.
    """
    if (
        _is_moving_toward(elevator, request.origin_floor)
        and elevator.direction == request.direction
    ):
        for index, stop in enumerate(elevator.stops):
            if (
                elevator.direction == Direction.UP
                and stop > request.origin_floor
            ) or (
                elevator.direction == Direction.DOWN
                and stop < request.origin_floor
            ):
                elevator.insert_stop(index, request.origin_floor)
                return

    elevator.add_stop(request.origin_floor)


class NearestSuitableCarDispatch(DispatchAlgorithm):
    """Direction-aware elevator dispatch.

    Prefers elevators that are already heading toward the caller
    in the matching direction. Falls back to idle elevators, then
    to less suitable candidates.

    See module docstring for the full suitability tier definition.
    """

    def dispatch(
        self,
        pending_requests: list[ElevatorRequest],
        elevators: list[Elevator],
        passengers: dict[str, Passenger] | None = None,
    ) -> list[DispatchResult]:
        """Assign pending requests using direction-aware suitability.

        Args:
            pending_requests: Unassigned hall-call requests.
            elevators: All elevators in the building.
            passengers: Optional passenger ID → Passenger lookup.

        Returns:
            List of ``DispatchResult`` for each new assignment.
        """
        if not elevators:
            return []

        # Process requests oldest-first, same as FCFS
        sorted_requests = sorted(
            pending_requests, key=lambda r: (r.timestamp, r.id)
        )

        results: list[DispatchResult] = []

        for request in sorted_requests:
            # Skip already-assigned requests
            if request.is_assigned:
                continue

            # Pick the most suitable elevator
            chosen = min(
                elevators,
                key=lambda e: _suitability_key(
                    e, request.origin_floor, request.direction
                ),
            )

            # Assign the request
            request.assigned_elevator_id = chosen.id
            if request.passenger_id is not None:
                if passengers is None:
                    raise ValueError(
                        "passengers is required for a request with passenger_id"
                    )
                passengers[request.passenger_id].assigned_elevator_id = chosen.id

            # The destination is added later via a CarRequest.
            _add_pickup_stop(chosen, request)

            results.append(
                DispatchResult(
                    request_id=request.id,
                    elevator_id=chosen.id,
                    passenger_id=request.passenger_id,
                )
            )

        return results
