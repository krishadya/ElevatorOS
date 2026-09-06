"""Tests for the SimulationEngine (Milestone 2).

These tests verify the deterministic tick-based simulation lifecycle:
movement, door state machine, passenger boarding/discharge, event
emission, and building state synchronization.
"""

import pytest

from app.simulation.building import Building
from app.simulation.clock import SimulationClock
from app.simulation.constants import (
    DOOR_CLOSING_TICKS,
    DOOR_OPEN_DWELL_TICKS,
    DOOR_OPENING_TICKS,
)
from app.simulation.elevator import Elevator
from app.simulation.engine import SimulationEngine
from app.simulation.enums import (
    Direction,
    DoorState,
    ElevatorState,
    EventType,
    PassengerState,
)
from app.simulation.passenger import Passenger
from app.simulation.request import ElevatorRequest


# ── Helpers ──────────────────────────────────────────────────────────


def _make_simple_building(
    num_floors: int = 10,
    num_elevators: int = 1,
    capacity: int = 8,
) -> Building:
    """Create a standard building for testing."""
    return Building.create(
        num_floors=num_floors,
        num_elevators=num_elevators,
        elevator_capacity=capacity,
    )


def _make_engine(building: Building) -> SimulationEngine:
    """Create an engine with a fresh clock."""
    return SimulationEngine(building=building, clock=SimulationClock())


def _tick_until(engine: SimulationEngine, max_ticks: int = 200) -> None:
    """Advance the engine until complete or max_ticks reached."""
    for _ in range(max_ticks):
        if engine.is_complete:
            break
        engine.tick()


def _events_of_type(
    events: list, event_type: EventType
) -> list:
    """Filter events by type."""
    return [e for e in events if e.event_type == event_type]


# ── Idle behavior ────────────────────────────────────────────────────


class TestEngineIdle:
    """Verify behavior when no stops are queued."""

    def test_idle_elevator_stays_idle(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        events = engine.tick()
        assert elev.state == ElevatorState.IDLE
        assert elev.direction == Direction.IDLE
        assert len(events) == 0

    def test_is_complete_when_no_work(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        assert engine.is_complete

    def test_is_not_complete_with_waiting_passengers(self):
        building = _make_simple_building()
        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        building.add_waiting_passenger(p)
        engine = _make_engine(building)
        assert not engine.is_complete

    def test_clock_advances_each_tick(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        assert engine.current_tick == 0
        engine.tick()
        assert engine.current_tick == 1
        engine.tick()
        assert engine.current_tick == 2


# ── Movement ─────────────────────────────────────────────────────────


class TestEngineMovement:
    """Verify tick-based elevator movement."""

    def test_move_to_stop(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(4)  # Elevator starts at floor 1
        engine.tick()  # Tick 0: IDLE → MOVING (depart)

        assert elev.state == ElevatorState.MOVING
        assert elev.direction == Direction.UP

        engine.tick()  # Tick 1: floor 1 → 2
        assert elev.current_floor == 2
        engine.tick()  # Tick 2: floor 2 → 3
        assert elev.current_floor == 3
        engine.tick()  # Tick 3: floor 3 → 4, arrive at stop
        assert elev.current_floor == 4
        assert elev.state == ElevatorState.STOPPED

    def test_move_down(self):
        building = _make_simple_building()
        elev = building.elevators[0]
        elev.current_floor = 5
        engine = _make_engine(building)

        elev.add_stop(3)
        engine.tick()  # IDLE → MOVING
        assert elev.direction == Direction.DOWN

        engine.tick()  # 5 → 4
        assert elev.current_floor == 4
        engine.tick()  # 4 → 3, arrive
        assert elev.current_floor == 3
        assert elev.state == ElevatorState.STOPPED

    def test_direction_update_between_stops(self):
        """Direction reverses between stops going different ways."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(3)
        elev.add_stop(1)  # After reaching 3, go back to 1

        # Run to completion
        _tick_until(engine)

        assert elev.current_floor == 1
        assert elev.state == ElevatorState.IDLE

    def test_no_movement_during_door_open(self):
        """Elevator must not move while doors are not CLOSED."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(2)
        engine.tick()  # IDLE → MOVING
        engine.tick()  # Move to floor 2, STOPPED, doors OPENING

        assert elev.state == ElevatorState.STOPPED
        assert elev.door_state in (DoorState.OPENING, DoorState.OPEN)
        # Elevator should not move — floor stays at 2
        saved_floor = elev.current_floor
        engine.tick()  # Process door opening
        assert elev.current_floor == saved_floor

    def test_floor_boundary_protection(self):
        """Engine doesn't crash at building boundaries."""
        building = Building.create(num_floors=3, num_elevators=1)
        engine = _make_engine(building)
        elev = building.elevators[0]

        # Go to top floor
        elev.add_stop(3)
        _tick_until(engine)
        assert elev.current_floor == 3

        # Go back to bottom
        elev.add_stop(1)
        _tick_until(engine)
        assert elev.current_floor == 1
        assert elev.state == ElevatorState.IDLE

    def test_events_emitted_during_movement(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(3)
        engine.tick()  # IDLE → MOVING, departed

        departed = _events_of_type(engine.events, EventType.ELEVATOR_DEPARTED)
        assert len(departed) == 1
        assert departed[0].elevator_id == "E1"

    def test_already_at_stop_goes_directly_to_stopped(self):
        """If the elevator is already at the stop floor, skip moving."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(1)  # Already at floor 1
        engine.tick()  # Should go to STOPPED immediately

        assert elev.state == ElevatorState.STOPPED
        assert elev.door_state in (DoorState.OPENING, DoorState.OPEN)


# ── Door state machine lifecycle ─────────────────────────────────────


class TestEngineDoorLifecycle:
    """Verify full door transition cycle through the engine."""

    def test_full_door_cycle_at_stop(self):
        """Doors go CLOSED → OPENING → OPEN → CLOSING → CLOSED at a stop."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(2)
        engine.tick()  # Tick 0: IDLE → MOVING (departed)
        engine.tick()  # Tick 1: move to 2, STOPPED, doors OPENING

        assert elev.state == ElevatorState.STOPPED
        assert elev.door_state == DoorState.OPENING

        # Process OPENING ticks
        for _ in range(DOOR_OPENING_TICKS):
            engine.tick()
        assert elev.door_state == DoorState.OPEN

        # OPEN phase: first tick is discharge (even if none), then dwell
        engine.tick()  # discharge tick (no passengers, builds boarding queue)
        for _ in range(DOOR_OPEN_DWELL_TICKS):
            engine.tick()

        assert elev.door_state == DoorState.CLOSING

        # Process CLOSING ticks
        for _ in range(DOOR_CLOSING_TICKS):
            engine.tick()
        assert elev.door_state == DoorState.CLOSED

    def test_door_events_emitted(self):
        """All four door events are emitted during a stop."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(2)
        _tick_until(engine)

        door_types = {
            EventType.DOORS_OPENING,
            EventType.DOORS_OPEN,
            EventType.DOORS_CLOSING,
            EventType.DOORS_CLOSED,
        }
        emitted_types = {e.event_type for e in engine.events}
        assert door_types.issubset(emitted_types)

    def test_elevator_goes_idle_after_last_stop(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(2)
        _tick_until(engine)

        assert elev.state == ElevatorState.IDLE
        assert elev.direction == Direction.IDLE
        assert elev.door_state == DoorState.CLOSED
        assert len(elev.stops) == 0

        idle_events = _events_of_type(engine.events, EventType.ELEVATOR_IDLE)
        assert len(idle_events) >= 1


# ── Hall-call lifecycle ─────────────────────────────────────────────


class TestEngineHallCallLifecycle:
    """Verify active hall calls are cleared once pickup doors open."""

    def test_assigned_hall_call_removed_when_doors_open_at_pickup(self):
        building = _make_simple_building(num_elevators=2)
        engine = _make_engine(building)
        e1 = building.elevators[0]

        served_call = ElevatorRequest(
            id="R1",
            origin_floor=2,
            direction=Direction.UP,
            timestamp=0,
            assigned_elevator_id="E1",
        )
        other_call = ElevatorRequest(
            id="R2",
            origin_floor=2,
            direction=Direction.UP,
            timestamp=0,
            assigned_elevator_id="E2",
        )
        building.add_request(served_call)
        building.add_request(other_call)
        e1.add_stop(2)

        for _ in range(50):
            events = engine.tick()
            if _events_of_type(events, EventType.DOORS_OPEN):
                break
        else:
            pytest.fail("Elevator did not open doors at the pickup floor")

        assert served_call not in building.active_requests
        assert building.active_requests == [other_call]


# ── Passenger discharge ─────────────────────────────────────────────


class TestEngineDischarge:
    """Verify passenger discharge at destination floors."""

    def test_passenger_discharged_at_destination(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        # Manually place a RIDING passenger going to floor 3
        p = Passenger(id="P1", origin_floor=1, destination_floor=3)
        p.state = PassengerState.RIDING
        p.assigned_elevator_id = "E1"
        elev.passengers.append(p)

        elev.add_stop(3)

        _tick_until(engine)

        assert p.state == PassengerState.ARRIVED
        assert p.dropoff_time is not None
        assert elev.passenger_count == 0

    def test_multiple_passengers_discharged_at_once(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p1 = Passenger(id="P1", origin_floor=1, destination_floor=3)
        p2 = Passenger(id="P2", origin_floor=2, destination_floor=3)
        for p in [p1, p2]:
            p.state = PassengerState.RIDING
            p.assigned_elevator_id = "E1"
            elev.passengers.append(p)

        elev.add_stop(3)
        _tick_until(engine)

        assert p1.state == PassengerState.ARRIVED
        assert p2.state == PassengerState.ARRIVED
        assert elev.passenger_count == 0

    def test_passenger_not_discharged_at_wrong_floor(self):
        """Passenger stays in elevator at intermediate stop."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.state = PassengerState.RIDING
        p.assigned_elevator_id = "E1"
        elev.passengers.append(p)

        elev.add_stop(3)  # Stop at 3, but passenger goes to 5
        _tick_until(engine)

        assert p.state == PassengerState.RIDING
        assert elev.passenger_count == 1

    def test_discharge_events_emitted(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=3)
        p.state = PassengerState.RIDING
        p.assigned_elevator_id = "E1"
        elev.passengers.append(p)

        elev.add_stop(3)
        _tick_until(engine)

        discharge_events = _events_of_type(
            engine.events, EventType.PASSENGER_DISCHARGED
        )
        assert len(discharge_events) == 1
        assert discharge_events[0].passenger_id == "P1"


# ── Passenger boarding ───────────────────────────────────────────────


class TestEngineBoarding:
    """Verify passenger boarding through the engine."""

    def test_passenger_boards_at_origin_floor(self):
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p)

        elev.add_stop(1)  # Stop at floor 1 (already there)
        _tick_until(engine)

        assert p.state == PassengerState.RIDING
        assert p.assigned_elevator_id == "E1"
        assert len(building.waiting_passengers) == 0
        assert p in elev.passengers

    def test_boarding_lifecycle_waiting_boarding_riding(self):
        """Verify passenger goes through WAITING → BOARDING → RIDING."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p)

        elev.add_stop(1)

        states_seen: list[PassengerState] = [p.state]
        for _ in range(50):
            if p.state == PassengerState.RIDING:
                break
            engine.tick()
            if p.state not in states_seen:
                states_seen.append(p.state)

        assert PassengerState.WAITING in states_seen
        assert PassengerState.BOARDING in states_seen
        assert PassengerState.RIDING in states_seen

    def test_one_passenger_boards_per_tick(self):
        """With multiple waiting passengers, only 1 boards per tick."""
        building = _make_simple_building(capacity=8)
        engine = _make_engine(building)
        elev = building.elevators[0]

        passengers = []
        for i in range(3):
            p = Passenger(id=f"P{i}", origin_floor=1, destination_floor=5)
            p.assigned_elevator_id = "E1"
            building.add_waiting_passenger(p)
            passengers.append(p)

        elev.add_stop(1)

        boarding_events = []
        for _ in range(50):
            events = engine.tick()
            boarding_events.extend(
                _events_of_type(events, EventType.PASSENGER_BOARDING)
            )
            if all(p.state == PassengerState.RIDING for p in passengers):
                break

        # Each PASSENGER_BOARDING event represents one passenger starting
        # to board. With 1/tick, boarding events should span multiple ticks.
        assert len(boarding_events) == 3

    def test_capacity_prevents_boarding(self):
        """When elevator is full, remaining passengers stay waiting."""
        building = _make_simple_building(capacity=1)
        engine = _make_engine(building)
        elev = building.elevators[0]

        p1 = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p2 = Passenger(id="P2", origin_floor=1, destination_floor=5)
        p1.assigned_elevator_id = "E1"
        p2.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p1)
        building.add_waiting_passenger(p2)

        elev.add_stop(1)
        _tick_until(engine)

        # Only 1 should have boarded
        boarded = [p for p in [p1, p2] if p.state in (PassengerState.RIDING, PassengerState.BOARDING)]
        waiting = [p for p in [p1, p2] if p.state == PassengerState.WAITING]
        assert len(boarded) == 1
        assert len(waiting) == 1

    def test_building_waiting_list_synchronized(self):
        """Boarded passengers are removed from building.waiting_passengers."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p)
        assert len(building.waiting_passengers) == 1

        elev.add_stop(1)
        _tick_until(engine)

        assert len(building.waiting_passengers) == 0

    def test_passenger_not_on_floor_not_boarded(self):
        """Passengers on a different floor don't board."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=5, destination_floor=8)
        p.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p)

        elev.add_stop(1)  # Stop at floor 1, passenger is on floor 5
        _tick_until(engine)

        assert p.state == PassengerState.WAITING
        assert len(building.waiting_passengers) == 1

    def test_unassigned_passenger_boards(self):
        """Passengers with assigned_elevator_id=None can board any elevator."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        # No assignment
        building.add_waiting_passenger(p)

        elev.add_stop(1)
        _tick_until(engine)

        assert p.state == PassengerState.RIDING
        assert p.assigned_elevator_id == "E1"

    def test_passenger_assigned_to_other_elevator_not_boarded(self):
        """Passenger assigned to E2 doesn't board E1."""
        building = _make_simple_building(num_elevators=2)
        engine = _make_engine(building)
        elev1 = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.assigned_elevator_id = "E2"
        building.add_waiting_passenger(p)

        elev1.add_stop(1)
        _tick_until(engine)

        assert p.state == PassengerState.WAITING
        assert len(building.waiting_passengers) == 1


# ── Full passenger journey ───────────────────────────────────────────


class TestEngineFullJourney:
    """Verify complete pickup-to-delivery journeys."""

    def test_single_passenger_journey(self):
        """One passenger: board at floor 1, ride to floor 5."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p)

        elev.add_stop(1)  # Pick up
        elev.add_stop(5)  # Drop off

        _tick_until(engine)

        assert p.state == PassengerState.ARRIVED
        assert p.dropoff_time is not None
        assert p.pickup_time is not None
        assert p.wait_time is not None
        assert p.ride_time is not None
        assert p.total_time is not None
        assert elev.passenger_count == 0
        assert elev.state == ElevatorState.IDLE
        assert len(building.waiting_passengers) == 0

    def test_multiple_stops_multiple_passengers(self):
        """Two passengers: P1 boards at 1→5, P2 boards at 3→7."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p1 = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p1.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p1)

        p2 = Passenger(id="P2", origin_floor=3, destination_floor=7)
        p2.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p2)

        elev.add_stop(1)  # Pick up P1
        elev.add_stop(3)  # Pick up P2
        elev.add_stop(5)  # Drop off P1
        elev.add_stop(7)  # Drop off P2

        _tick_until(engine)

        assert p1.state == PassengerState.ARRIVED
        assert p2.state == PassengerState.ARRIVED
        assert elev.passenger_count == 0
        assert elev.state == ElevatorState.IDLE


# ── Deterministic replay ────────────────────────────────────────────


class TestEngineDeterminism:
    """Verify identical inputs produce identical outputs."""

    def _run_scenario(self) -> list:
        """Run a standard scenario and return events."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        p = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p)

        elev.add_stop(1)
        elev.add_stop(5)

        _tick_until(engine)
        return engine.events

    def test_deterministic_replay(self):
        """Two runs of the same scenario produce identical event sequences."""
        events_1 = self._run_scenario()
        events_2 = self._run_scenario()

        assert len(events_1) == len(events_2)
        for e1, e2 in zip(events_1, events_2):
            assert e1.tick == e2.tick
            assert e1.event_type == e2.event_type
            assert e1.elevator_id == e2.elevator_id
            assert e1.floor == e2.floor
            assert e1.passenger_id == e2.passenger_id

    def test_clock_state_after_replay(self):
        """Clock state is identical after identical runs."""
        building1 = _make_simple_building()
        clock1 = SimulationClock()
        engine1 = SimulationEngine(building=building1, clock=clock1)
        building1.elevators[0].add_stop(3)
        _tick_until(engine1)

        building2 = _make_simple_building()
        clock2 = SimulationClock()
        engine2 = SimulationEngine(building=building2, clock=clock2)
        building2.elevators[0].add_stop(3)
        _tick_until(engine2)

        assert clock1.current_tick == clock2.current_tick


# ── Multi-elevator ───────────────────────────────────────────────────


class TestEngineMultiElevator:
    """Verify engine handles multiple elevators independently."""

    def test_two_elevators_independent_routes(self):
        building = _make_simple_building(num_elevators=2)
        engine = _make_engine(building)
        e1, e2 = building.elevators

        e1.add_stop(5)
        e2.add_stop(3)

        _tick_until(engine)

        assert e1.current_floor == 5
        assert e2.current_floor == 3
        assert e1.state == ElevatorState.IDLE
        assert e2.state == ElevatorState.IDLE

    def test_two_elevators_with_passengers(self):
        building = _make_simple_building(num_elevators=2)
        engine = _make_engine(building)
        e1, e2 = building.elevators

        p1 = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p1.assigned_elevator_id = "E1"
        building.add_waiting_passenger(p1)

        p2 = Passenger(id="P2", origin_floor=1, destination_floor=3)
        p2.assigned_elevator_id = "E2"
        building.add_waiting_passenger(p2)

        e1.add_stop(1)
        e1.add_stop(5)
        e2.add_stop(1)
        e2.add_stop(3)

        _tick_until(engine)

        assert p1.state == PassengerState.ARRIVED
        assert p2.state == PassengerState.ARRIVED
        assert e1.passenger_count == 0
        assert e2.passenger_count == 0


# ── Regression Tests ─────────────────────────────────────────────────


class TestEngineRegression:
    """Verify bug fixes for Milestone 2 reviews."""

    def test_capacity_doors_do_not_freeze(self):
        """CRITICAL #1: Elevator at capacity with remaining queue must still close doors."""
        building = _make_simple_building(capacity=1)
        engine = _make_engine(building)
        elev = building.elevators[0]

        p1 = Passenger(id="P1", origin_floor=1, destination_floor=5)
        p2 = Passenger(id="P2", origin_floor=1, destination_floor=5)
        building.add_waiting_passenger(p1)
        building.add_waiting_passenger(p2)

        elev.add_stop(1)
        elev.add_stop(5)

        _tick_until(engine)

        assert p1.state == PassengerState.ARRIVED
        assert p2.state == PassengerState.WAITING  # P2 was left behind
        assert elev.state == ElevatorState.IDLE  # Did not freeze with doors OPEN

    def test_duplicate_stops_in_route(self):
        """CRITICAL #2: Duplicate stops must be executed sequentially."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(5)
        elev.add_stop(2)
        elev.add_stop(5)

        _tick_until(engine)

        assert elev.current_floor == 5
        assert elev.state == ElevatorState.IDLE
        # 3 stops total, means 3 DOORS_OPEN events
        open_events = _events_of_type(engine.events, EventType.DOORS_OPEN)
        assert len(open_events) == 3

    def test_back_to_back_stops_at_same_floor(self):
        """IMPORTANT #1: next_stop == current_floor must reopen doors, not move DOWN."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(5)
        elev.add_stop(5)

        _tick_until(engine)

        assert elev.current_floor == 5
        assert elev.state == ElevatorState.IDLE
        open_events = _events_of_type(engine.events, EventType.DOORS_OPEN)
        assert len(open_events) == 2

    def test_passenger_arriving_during_door_dwell_boards(self):
        """IMPORTANT #2: Passengers added during OPEN phase should board."""
        building = _make_simple_building()
        engine = _make_engine(building)
        elev = building.elevators[0]

        elev.add_stop(2)

        # tick until doors are OPEN at floor 2
        for _ in range(50):
            engine.tick()
            if elev.current_floor == 2 and elev.door_state == DoorState.OPEN:
                break

        # Doors are now OPEN. Add a new passenger!
        p = Passenger(id="P1", origin_floor=2, destination_floor=5)
        building.add_waiting_passenger(p)
        elev.add_stop(5)  # tell elevator to go drop them off

        _tick_until(engine)

        assert p.state == PassengerState.ARRIVED
        assert p.dropoff_time is not None
