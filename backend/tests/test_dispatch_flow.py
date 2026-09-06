"""Integration tests proving the flow of Hall Call followed by Car Request."""

from app.algorithms.fcfs import FCFSDispatch
from app.simulation.building import Building
from app.simulation.car_request import CarRequest, process_car_request
from app.simulation.enums import Direction
from app.simulation.passenger import Passenger
from app.simulation.request import ElevatorRequest


def test_hall_call_then_car_request_flow() -> None:
    """Proves the exact flow:
    1. Hall Call: Floor 6 UP -> dispatch chooses elevator -> ONLY Floor 6 is added
    2. Later: CarRequest -> Floor 9 -> Floor 9 is added to that elevator only
    """
    building = Building.create(num_floors=10, num_elevators=2)
    e1 = building.get_elevator("E1")
    e2 = building.get_elevator("E2")
    assert e1 is not None and e2 is not None

    # E1 starts at 1, E2 starts at 1
    # 1. Hall Call: Floor 6 UP
    p1 = Passenger(
        id="P1",
        origin_floor=6,
        destination_floor=9,
        arrival_time=0,
    )
    hc = ElevatorRequest(
        id="HC1",
        origin_floor=6,
        direction=Direction.UP,
        timestamp=0,
        passenger_id="P1",
    )

    algo = FCFSDispatch()
    results = algo.dispatch(
        pending_requests=[hc],
        elevators=[e1, e2],
        passengers={"P1": p1},
    )

    # Dispatch chooses E1 (tie-break goes to E1)
    assert len(results) == 1
    assert results[0].elevator_id == "E1"
    
    # ONLY Floor 6 is added to E1, E2 is untouched
    assert e1.stops == [6]
    assert e2.stops == []

    # 2. Later: Passenger boards E1 and presses 9 (CarRequest)
    cr = CarRequest(
        id="CR1",
        elevator_id="E1",
        destination_floor=9,
        timestamp=10,
    )
    process_car_request(cr, building)

    # Floor 9 is added to E1 only
    assert e1.stops == [6, 9]
    assert e2.stops == []
