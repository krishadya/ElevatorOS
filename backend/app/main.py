"""Minimal FastAPI facade for the in-memory ElevatorOS simulation.

The API owns only the current demo session. Domain models, dispatch
algorithms, and the deterministic engine remain framework-independent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.algorithms.base import DispatchAlgorithm
from app.algorithms.fcfs import FCFSDispatch
from app.algorithms.nearest_car import NearestSuitableCarDispatch
from app.simulation.building import Building
from app.simulation.car_request import CarRequest, process_car_request
from app.simulation.engine import SimulationEngine
from app.simulation.enums import Direction
from app.simulation.request import ElevatorRequest


DEFAULT_FLOORS = 10
DEFAULT_ELEVATORS = 2
RECENT_EVENT_LIMIT = 10


class HallCallInput(BaseModel):
    """Input for a passenger-free hallway call."""

    floor: int
    direction: Literal["UP", "DOWN"]


class CarRequestInput(BaseModel):
    """Input for an in-car destination selection."""

    elevator_id: str
    destination_floor: int


class AlgorithmInput(BaseModel):
    """Input for selecting the algorithm for future hall calls."""

    algorithm: str


@dataclass
class SimulationSession:
    """The single, resettable in-memory simulation exposed by the API."""

    building: Building
    engine: SimulationEngine
    algorithm_name: str
    algorithm: DispatchAlgorithm
    next_hall_call_id: int = 1
    next_car_request_id: int = 1

    @classmethod
    def create_default(cls) -> SimulationSession:
        """Create the deterministic default building and FCFS selection."""
        building = Building.create(
            num_floors=DEFAULT_FLOORS,
            num_elevators=DEFAULT_ELEVATORS,
        )
        return cls(
            building=building,
            engine=SimulationEngine(building=building),
            algorithm_name="fcfs",
            algorithm=FCFSDispatch(),
        )

    def select_algorithm(self, name: str) -> None:
        """Select a dispatch algorithm for future hall calls only."""
        if name == "fcfs":
            self.algorithm_name = name
            self.algorithm = FCFSDispatch()
            return
        if name == "nearest":
            self.algorithm_name = name
            self.algorithm = NearestSuitableCarDispatch()
            return
        raise ValueError(f"Unknown algorithm '{name}'. Use 'fcfs' or 'nearest'.")


app = FastAPI(title="ElevatorOS API")
app.state.simulation = SimulationSession.create_default()


def _session(request: Request) -> SimulationSession:
    """Return the current application-owned simulation session."""
    return request.app.state.simulation


def _hall_call_payload(call: ElevatorRequest) -> dict[str, object]:
    """Serialize the UI-facing hall-call fields without passenger details."""
    return {
        "id": call.id,
        "floor": call.origin_floor,
        "direction": call.direction.name,
        "assigned_elevator": call.assigned_elevator_id,
    }


def _state_payload(session: SimulationSession) -> dict[str, object]:
    """Serialize the minimal simulation state needed by the visualizer."""
    return {
        "tick": session.engine.current_tick,
        "time": session.engine.clock.time,
        "algorithm": session.algorithm_name,
        "elevators": [
            {
                "id": elevator.id,
                "current_floor": elevator.current_floor,
                "direction": elevator.direction.name,
                "state": elevator.state.name,
                "door_state": elevator.door_state.name,
                "stops": list(elevator.stops),
            }
            for elevator in session.building.elevators
        ],
        "active_hall_calls": [
            _hall_call_payload(call)
            for call in session.building.active_requests
        ],
        "recent_events": [
            {
                "tick": event.tick,
                "type": event.event_type.name,
                "elevator_id": event.elevator_id,
                "floor": event.floor,
                "passenger_id": event.passenger_id,
            }
            for event in session.engine.events[-RECENT_EVENT_LIMIT:]
        ],
    }


def _validate_floor(session: SimulationSession, floor: int) -> None:
    """Raise a clear API error when a floor is outside the building."""
    if not session.building.is_valid_floor(floor):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Floor {floor} is outside building range "
                f"[{session.building.min_floor}, {session.building.max_floor}]."
            ),
        )


@app.get("/state")
def get_state(request: Request) -> dict[str, object]:
    """Return the current in-memory simulation state."""
    return _state_payload(_session(request))


@app.post("/hall-call")
def create_hall_call(
    body: HallCallInput, request: Request
) -> dict[str, object]:
    """Register and dispatch a passenger-free hall call."""
    session = _session(request)
    _validate_floor(session, body.floor)

    call = ElevatorRequest(
        id=f"HC{session.next_hall_call_id}",
        origin_floor=body.floor,
        direction=Direction[body.direction],
        timestamp=session.engine.current_tick,
    )
    session.next_hall_call_id += 1
    session.building.add_request(call)

    assignments = session.algorithm.dispatch(
        pending_requests=[call],
        elevators=session.building.elevators,
    )
    if not assignments:
        raise HTTPException(
            status_code=409,
            detail="No elevators are available to serve the hall call.",
        )

    return {
        "hall_call": _hall_call_payload(call),
        "assignment": {"elevator_id": assignments[0].elevator_id},
    }


@app.post("/car-request")
def create_car_request(
    body: CarRequestInput, request: Request
) -> dict[str, object]:
    """Add an in-car destination to one selected elevator's route."""
    session = _session(request)
    _validate_floor(session, body.destination_floor)
    elevator = session.building.get_elevator(body.elevator_id)
    if elevator is None:
        raise HTTPException(
            status_code=404,
            detail=f"Elevator '{body.elevator_id}' was not found.",
        )

    car_request = CarRequest(
        id=f"CR{session.next_car_request_id}",
        elevator_id=body.elevator_id,
        destination_floor=body.destination_floor,
        timestamp=session.engine.current_tick,
    )
    session.next_car_request_id += 1
    process_car_request(car_request, session.building)

    return {
        "car_request": {
            "id": car_request.id,
            "elevator_id": car_request.elevator_id,
            "destination_floor": car_request.destination_floor,
        },
        "stops": list(elevator.stops),
    }


@app.post("/tick")
def tick(request: Request) -> dict[str, object]:
    """Advance the simulation by exactly one deterministic tick."""
    session = _session(request)
    session.engine.tick()
    return _state_payload(session)


@app.post("/reset")
def reset(request: Request) -> dict[str, object]:
    """Replace the session with the default empty deterministic simulation."""
    request.app.state.simulation = SimulationSession.create_default()
    return _state_payload(_session(request))


@app.post("/algorithm")
def select_algorithm(
    body: AlgorithmInput, request: Request
) -> dict[str, str]:
    """Select FCFS or nearest suitable car for future hall calls."""
    session = _session(request)
    try:
        session.select_algorithm(body.algorithm)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"algorithm": session.algorithm_name}
