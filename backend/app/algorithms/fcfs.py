"""First-Come, First-Served (FCFS) dispatch algorithm for ElevatorOS.

FCFS is the simplest possible dispatch strategy and serves as the
baseline for benchmarking future algorithms. It processes requests
in arrival order and assigns each to the elevator with the fewest
queued stops, with no consideration of distance or direction.

How it works:
    1. Sort pending requests by (timestamp, request_id) — oldest first,
       with lexicographic tie-breaking on ID for determinism.
    2. Skip any request that is already assigned.
    3. For each unassigned request, pick the elevator with the fewest
       stops. Ties are broken by elevator ID (lexicographic).
    4. Append the pickup floor, then the destination floor, to the
       chosen elevator's stop list.
    5. Mark the request and passenger as assigned to that elevator.
"""

from __future__ import annotations

from app.simulation.elevator import Elevator
from app.simulation.passenger import Passenger
from app.simulation.request import ElevatorRequest

from app.algorithms.base import DispatchAlgorithm, DispatchResult


class FCFSDispatch(DispatchAlgorithm):
    """First-Come, First-Served elevator dispatch.

    Intentionally basic — exists as a baseline for comparison.
    Does NOT optimize for distance, direction, or load.
    """

    def dispatch(
        self,
        pending_requests: list[ElevatorRequest],
        elevators: list[Elevator],
        passengers: dict[str, Passenger],
    ) -> list[DispatchResult]:
        """Assign pending requests oldest-first.

        Args:
            pending_requests: Unassigned hall-call requests.
            elevators: All elevators in the building.
            passengers: Passenger ID → Passenger lookup.

        Returns:
            List of ``DispatchResult`` for each new assignment.
        """
        if not elevators:
            return []

        # Sort by (timestamp, id) for deterministic oldest-first ordering
        sorted_requests = sorted(
            pending_requests, key=lambda r: (r.timestamp, r.id)
        )

        results: list[DispatchResult] = []

        for request in sorted_requests:
            # Skip already-assigned requests
            if request.is_assigned:
                continue

            # Pick elevator with fewest stops, tie-break on elevator ID
            chosen = min(elevators, key=lambda e: (len(e.stops), e.id))

            # Look up the passenger to get destination floor
            passenger = passengers[request.passenger_id]

            # Assign the request
            request.assigned_elevator_id = chosen.id
            passenger.assigned_elevator_id = chosen.id

            # Add pickup floor, then destination floor to the route
            chosen.add_stop(passenger.origin_floor)
            chosen.add_stop(passenger.destination_floor)

            results.append(
                DispatchResult(
                    request_id=request.id,
                    elevator_id=chosen.id,
                    passenger_id=passenger.id,
                )
            )

        return results
