"""Car request model for ElevatorOS.

A CarRequest represents a destination floor button press inside a
specific elevator. Unlike a hall call (``ElevatorRequest``), a car
request already belongs to a known elevator and does NOT require
dispatch — it goes directly to that elevator's stop list.

Hall Call vs Car Request:

    Hall Call (``ElevatorRequest``):
        Someone standing in the hallway presses UP or DOWN.
        A dispatch algorithm must choose which elevator to send.

    Car Request (``CarRequest``):
        Someone already inside elevator E2 presses "Floor 5".
        Floor 5 is added to E2's route. No dispatch needed.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.simulation.building import Building


@dataclass
class CarRequest:
    """A destination floor request made inside a specific elevator.

    Attributes:
        id: Unique request identifier.
        elevator_id: ID of the elevator the passenger is inside.
        destination_floor: Floor the passenger wants to reach.
        timestamp: Simulation tick when the button was pressed.
    """

    id: str
    elevator_id: str
    destination_floor: int
    timestamp: int


def process_car_request(car_request: CarRequest, building: Building) -> None:
    """Process a car request by adding the destination to the elevator's route.

    This bypasses all dispatch logic. The destination floor is appended
    directly to the named elevator's stop list.

    Args:
        car_request: The in-car destination request.
        building: The building containing the elevator.

    Raises:
        ValueError: If the elevator ID does not exist in the building.
        ValueError: If the destination floor is outside the elevator's range.
    """
    elevator = building.get_elevator(car_request.elevator_id)
    if elevator is None:
        raise ValueError(
            f"Elevator '{car_request.elevator_id}' not found in building."
        )

    # add_stop validates floor bounds and raises ValueError if invalid
    elevator.add_stop(car_request.destination_floor)
