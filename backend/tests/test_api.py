"""API tests for the in-memory ElevatorOS FastAPI facade."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        test_client.post("/reset")
        yield test_client


def test_state_starts_with_default_simulation(client: TestClient) -> None:
    response = client.get("/state")

    assert response.status_code == 200
    state = response.json()
    assert state["tick"] == 0
    assert state["time"] == 0
    assert state["algorithm"] == "fcfs"
    assert state["active_hall_calls"] == []
    assert [elevator["id"] for elevator in state["elevators"]] == ["E1", "E2"]
    assert all(elevator["stops"] == [] for elevator in state["elevators"])


def test_hall_call_dispatches_through_fcfs_without_destination(
    client: TestClient,
) -> None:
    response = client.post("/hall-call", json={"floor": 6, "direction": "UP"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["hall_call"] == {
        "id": "HC1",
        "floor": 6,
        "direction": "UP",
        "assigned_elevator": "E1",
    }
    assert payload["assignment"] == {"elevator_id": "E1"}
    assert "destination" not in payload["hall_call"]


def test_hall_call_dispatches_through_nearest_algorithm(
    client: TestClient,
) -> None:
    assert client.post("/algorithm", json={"algorithm": "nearest"}).status_code == 200

    response = client.post("/hall-call", json={"floor": 6, "direction": "UP"})

    assert response.status_code == 200
    assert response.json()["assignment"] == {"elevator_id": "E1"}
    assert client.get("/state").json()["algorithm"] == "nearest"


def test_active_hall_call_appears_after_creation(client: TestClient) -> None:
    client.post("/hall-call", json={"floor": 4, "direction": "DOWN"})

    calls = client.get("/state").json()["active_hall_calls"]
    assert calls == [
        {
            "id": "HC1",
            "floor": 4,
            "direction": "DOWN",
            "assigned_elevator": "E1",
        }
    ]


def test_tick_advances_exactly_one_tick(client: TestClient) -> None:
    response = client.post("/tick")

    assert response.status_code == 200
    assert response.json()["tick"] == 1
    assert response.json()["time"] == 1


def test_active_call_disappears_after_assigned_car_opens_at_pickup(
    client: TestClient,
) -> None:
    client.post("/hall-call", json={"floor": 2, "direction": "UP"})

    for _ in range(10):
        state = client.post("/tick").json()
        if not state["active_hall_calls"]:
            break

    assert state["active_hall_calls"] == []
    assert any(event["type"] == "DOORS_OPEN" for event in state["recent_events"])


def test_car_request_only_changes_the_named_elevator(client: TestClient) -> None:
    response = client.post(
        "/car-request",
        json={"elevator_id": "E2", "destination_floor": 8},
    )

    assert response.status_code == 200
    assert response.json()["stops"] == [8]
    elevators = client.get("/state").json()["elevators"]
    assert elevators[0]["stops"] == []
    assert elevators[1]["stops"] == [8]


def test_algorithm_switch_only_changes_future_hall_call_selection(
    client: TestClient,
) -> None:
    first_call = client.post(
        "/hall-call", json={"floor": 3, "direction": "UP"}
    ).json()

    response = client.post("/algorithm", json={"algorithm": "nearest"})

    assert response.status_code == 200
    assert response.json() == {"algorithm": "nearest"}
    assert client.get("/state").json()["active_hall_calls"][0] == first_call[
        "hall_call"
    ]


def test_reset_restores_the_default_empty_simulation(client: TestClient) -> None:
    client.post("/algorithm", json={"algorithm": "nearest"})
    client.post("/hall-call", json={"floor": 6, "direction": "UP"})
    client.post("/tick")

    response = client.post("/reset")

    assert response.status_code == 200
    assert response.json()["tick"] == 0
    assert response.json()["algorithm"] == "fcfs"
    assert response.json()["active_hall_calls"] == []
    assert all(elevator["stops"] == [] for elevator in response.json()["elevators"])


def test_invalid_floor_and_direction_return_clear_errors(client: TestClient) -> None:
    invalid_floor = client.post(
        "/hall-call", json={"floor": 11, "direction": "UP"}
    )
    invalid_direction = client.post(
        "/hall-call", json={"floor": 5, "direction": "SIDEWAYS"}
    )

    assert invalid_floor.status_code == 422
    assert "outside building range" in invalid_floor.json()["detail"]
    assert invalid_direction.status_code == 422


def test_invalid_elevator_and_algorithm_return_clear_errors(client: TestClient) -> None:
    invalid_elevator = client.post(
        "/car-request",
        json={"elevator_id": "E99", "destination_floor": 5},
    )
    invalid_algorithm = client.post("/algorithm", json={"algorithm": "other"})

    assert invalid_elevator.status_code == 404
    assert "was not found" in invalid_elevator.json()["detail"]
    assert invalid_algorithm.status_code == 422
    assert "Unknown algorithm" in invalid_algorithm.json()["detail"]


def test_identical_api_sequences_produce_identical_states(
    client: TestClient,
) -> None:
    def run_sequence() -> list[dict[str, object]]:
        client.post("/reset")
        responses = [
            client.post("/hall-call", json={"floor": 2, "direction": "UP"}).json()
        ]
        responses.extend(client.post("/tick").json() for _ in range(3))
        return responses

    assert run_sequence() == run_sequence()
