"""Dispatch algorithm interface for ElevatorOS.

Defines the contract that all dispatch algorithms must satisfy.
Algorithms receive pending requests and available elevators, then
decide which elevator handles each request. They operate externally
on domain models via public methods (e.g. ``add_stop()``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.simulation.elevator import Elevator
    from app.simulation.passenger import Passenger
    from app.simulation.request import ElevatorRequest


@dataclass(frozen=True)
class DispatchResult:
    """Record of a single dispatch assignment.

    Attributes:
        request_id: ID of the ElevatorRequest that was assigned.
        elevator_id: ID of the Elevator chosen to serve this request.
        passenger_id: Optional ID of the Passenger associated with this request.
    """

    request_id: str
    elevator_id: str
    passenger_id: str | None


class DispatchAlgorithm(ABC):
    """Abstract base class for elevator dispatch algorithms.

    Subclasses implement ``dispatch()`` to assign pending hall-call
    requests to elevators.  The algorithm must:

    - Only assign requests that are not already assigned.
    - Set ``request.assigned_elevator_id`` for each assignment. If the
      request is associated with a Passenger, set that passenger's
      ``assigned_elevator_id`` as well.
    - Add ONLY the pickup floor (``request.origin_floor``) to the
      chosen elevator's stop list. Direction-aware algorithms may insert an
      en-route pickup before a farther stop via ``elevator.insert_stop()``.
      The destination floor is added later via a ``CarRequest``
      when the passenger enters the elevator and selects a floor.
    - Not remove existing stops or otherwise reorder them.
    """

    @abstractmethod
    def dispatch(
        self,
        pending_requests: list[ElevatorRequest],
        elevators: list[Elevator],
        passengers: dict[str, Passenger] | None = None,
    ) -> list[DispatchResult]:
        """Assign pending requests to elevators.

        Args:
            pending_requests: Unassigned ``ElevatorRequest`` objects.
            elevators: All available elevators in the building.
            passengers: Optional lookup from passenger ID to ``Passenger``.
                It is only needed when requests carry ``passenger_id`` values.

        Returns:
            A list of ``DispatchResult`` recording each assignment made.
        """
