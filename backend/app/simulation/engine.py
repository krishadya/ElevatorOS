"""Deterministic simulation engine for ElevatorOS.

The engine is the orchestrator: it advances the clock, drives elevator
state transitions, and coordinates building/elevator/passenger state.

It does NOT contain scheduling logic. Stops must be pre-loaded into
each elevator's ``stops`` list by an external algorithm before or
during the simulation run. The engine only executes the route.

Tick lifecycle (per elevator, in order):
    1. IDLE  → if stops exist, set direction, transition to MOVING
    2. MOVING → move_one_floor(); if at next stop → STOPPED, begin OPENING
    3. STOPPED → advance door/passenger lifecycle:
       a. OPENING  → decrement timer → OPEN
       b. OPEN     → discharge all eligible → board 1/tick → when done → CLOSING
       c. CLOSING  → decrement timer → CLOSED → remove stop
                     → more stops? MOVING : IDLE
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.simulation.building import Building
from app.simulation.clock import SimulationClock
from app.simulation.constants import (
    DOOR_CLOSING_TICKS,
    DOOR_OPEN_DWELL_TICKS,
    DOOR_OPENING_TICKS,
    PASSENGERS_BOARDING_PER_TICK,
)
from app.simulation.elevator import Elevator
from app.simulation.enums import (
    Direction,
    DoorState,
    ElevatorState,
    EventType,
    PassengerState,
)
from app.simulation.events import SimulationEvent
from app.simulation.passenger import Passenger


@dataclass
class _ElevatorRuntime:
    """Per-elevator mutable state tracked by the engine.

    This is internal bookkeeping — not part of the public domain model.

    Attributes:
        door_timer: Ticks remaining in the current door phase.
        discharged_this_stop: Whether discharge has happened at this stop.
        boarding_queue: Passengers eligible to board at this stop.
        dwell_remaining: Ticks of mandatory dwell time remaining.
    """

    door_timer: int = 0
    discharged_this_stop: bool = False
    boarding_queue: list[Passenger] = field(default_factory=list)
    dwell_remaining: int = 0


@dataclass
class SimulationEngine:
    """Deterministic simulation engine.

    Coordinates the Building, Elevators, Clock, and Passengers through
    tick-based state transitions. Does not decide routing — only
    executes pre-loaded stops.

    Attributes:
        building: The building being simulated.
        clock: The deterministic simulation clock.
        events: Chronological list of all events emitted during the run.
    """

    building: Building
    clock: SimulationClock = field(default_factory=SimulationClock)
    events: list[SimulationEvent] = field(default_factory=list)
    _runtimes: dict[str, _ElevatorRuntime] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        for elev in self.building.elevators:
            self._runtimes[elev.id] = _ElevatorRuntime()

    # ── Public API ───────────────────────────────────────────────────

    def tick(self) -> list[SimulationEvent]:
        """Advance the simulation by one clock step.

        Processes all elevators, then advances the clock.

        Returns:
            List of events that occurred during this tick.
        """
        tick_events: list[SimulationEvent] = []
        current_tick = self.clock.current_tick

        for elev in self.building.elevators:
            rt = self._runtimes[elev.id]
            events = self._process_elevator(elev, rt, current_tick)
            tick_events.extend(events)

        self.events.extend(tick_events)
        self.clock.tick()
        return tick_events

    @property
    def current_tick(self) -> int:
        """The current simulation tick (before next advancement)."""
        return self.clock.current_tick

    @property
    def is_complete(self) -> bool:
        """Whether all elevators are idle with no stops and no passengers waiting."""
        all_idle = all(
            e.state == ElevatorState.IDLE and len(e.stops) == 0
            for e in self.building.elevators
        )
        no_waiting = len(self.building.waiting_passengers) == 0
        return all_idle and no_waiting

    # ── Per-elevator tick processing ─────────────────────────────────

    def _process_elevator(
        self,
        elev: Elevator,
        rt: _ElevatorRuntime,
        current_tick: int,
    ) -> list[SimulationEvent]:
        """Process one tick of the elevator lifecycle."""
        events: list[SimulationEvent] = []

        if elev.state == ElevatorState.IDLE:
            self._process_idle(elev, rt, current_tick, events)
        elif elev.state == ElevatorState.MOVING:
            self._process_moving(elev, rt, current_tick, events)
        elif elev.state == ElevatorState.STOPPED:
            self._process_stopped(elev, rt, current_tick, events)

        return events

    def _process_idle(
        self,
        elev: Elevator,
        rt: _ElevatorRuntime,
        current_tick: int,
        events: list[SimulationEvent],
    ) -> None:
        """IDLE: check for stops, begin moving if any exist."""
        if not elev.stops:
            return

        next_stop = elev.stops[0]

        # Already at the first stop — go directly to STOPPED
        if next_stop == elev.current_floor:
            elev.state = ElevatorState.STOPPED
            elev.open_doors()
            rt.door_timer = DOOR_OPENING_TICKS
            rt.discharged_this_stop = False
            rt.boarding_queue = []
            rt.dwell_remaining = DOOR_OPEN_DWELL_TICKS
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.ELEVATOR_STOPPED,
                elevator_id=elev.id,
                floor=elev.current_floor,
            ))
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.DOORS_OPENING,
                elevator_id=elev.id,
                floor=elev.current_floor,
            ))
            return

        # Set direction toward the first stop
        if next_stop > elev.current_floor:
            elev.direction = Direction.UP
        else:
            elev.direction = Direction.DOWN

        elev.state = ElevatorState.MOVING
        events.append(SimulationEvent(
            tick=current_tick,
            event_type=EventType.ELEVATOR_DEPARTED,
            elevator_id=elev.id,
            floor=elev.current_floor,
            details=f"Heading {elev.direction.name} toward floor {next_stop}",
        ))

    def _process_moving(
        self,
        elev: Elevator,
        rt: _ElevatorRuntime,
        current_tick: int,
        events: list[SimulationEvent],
    ) -> None:
        """MOVING: advance one floor, check if we've arrived at a stop."""
        elev.move_one_floor()
        events.append(SimulationEvent(
            tick=current_tick,
            event_type=EventType.ELEVATOR_MOVED,
            elevator_id=elev.id,
            floor=elev.current_floor,
        ))

        # Check if we've arrived at the next stop
        if elev.stops and elev.current_floor == elev.stops[0]:
            elev.state = ElevatorState.STOPPED
            elev.open_doors()
            rt.door_timer = DOOR_OPENING_TICKS
            rt.discharged_this_stop = False
            rt.boarding_queue = []
            rt.dwell_remaining = DOOR_OPEN_DWELL_TICKS
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.ELEVATOR_STOPPED,
                elevator_id=elev.id,
                floor=elev.current_floor,
            ))
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.DOORS_OPENING,
                elevator_id=elev.id,
                floor=elev.current_floor,
            ))

    def _process_stopped(
        self,
        elev: Elevator,
        rt: _ElevatorRuntime,
        current_tick: int,
        events: list[SimulationEvent],
    ) -> None:
        """STOPPED: advance the door/passenger lifecycle."""
        if elev.door_state == DoorState.OPENING:
            self._process_door_opening(elev, rt, current_tick, events)
        elif elev.door_state == DoorState.OPEN:
            self._process_door_open(elev, rt, current_tick, events)
        elif elev.door_state == DoorState.CLOSING:
            self._process_door_closing(elev, rt, current_tick, events)

    def _process_door_opening(
        self,
        elev: Elevator,
        rt: _ElevatorRuntime,
        current_tick: int,
        events: list[SimulationEvent],
    ) -> None:
        """OPENING phase: count down timer, then transition to OPEN."""
        rt.door_timer -= 1
        if rt.door_timer <= 0:
            elev.finish_opening()
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.DOORS_OPEN,
                elevator_id=elev.id,
                floor=elev.current_floor,
            ))

    def _process_door_open(
        self,
        elev: Elevator,
        rt: _ElevatorRuntime,
        current_tick: int,
        events: list[SimulationEvent],
    ) -> None:
        """OPEN phase: discharge, then board 1/tick, then begin closing."""
        # Step 1: Discharge all passengers at destination (all-at-once)
        if not rt.discharged_this_stop:
            rt.discharged_this_stop = True
            discharged = elev.discharge_passengers_at_destination(current_tick)
            for p in discharged:
                events.append(SimulationEvent(
                    tick=current_tick,
                    event_type=EventType.PASSENGER_DISCHARGED,
                    elevator_id=elev.id,
                    floor=elev.current_floor,
                    passenger_id=p.id,
                    details=f"Arrived at destination floor {p.destination_floor}",
                ))

            # Build the boarding queue: waiting passengers assigned to
            # this elevator at the current floor
            rt.boarding_queue = [
                p for p in self.building.waiting_passengers
                if (
                    p.origin_floor == elev.current_floor
                    and p.state == PassengerState.WAITING
                    and (
                        p.assigned_elevator_id is None
                        or p.assigned_elevator_id == elev.id
                    )
                )
            ]
            return  # Discharge tick; boarding starts next tick

        # Re-evaluate eligible waiting passengers each OPEN tick so that
        # passengers who arrive after doors opened can still board.
        newly_eligible = [
            p for p in self.building.waiting_passengers
            if (
                p.origin_floor == elev.current_floor
                and p.state == PassengerState.WAITING
                and (
                    p.assigned_elevator_id is None
                    or p.assigned_elevator_id == elev.id
                )
                and p not in rt.boarding_queue
            )
        ]
        rt.boarding_queue.extend(newly_eligible)

        # Step 2: Finish boarding passengers who started boarding last tick
        boarding_passengers = [
            p for p in elev.passengers
            if p.state == PassengerState.BOARDING
        ]
        for p in boarding_passengers:
            elev.finish_boarding(p)
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.PASSENGER_BOARDED,
                elevator_id=elev.id,
                floor=elev.current_floor,
                passenger_id=p.id,
                details=f"Boarded, heading to floor {p.destination_floor}",
            ))

        # Step 3: Begin boarding the next batch (1 per tick)
        boarded_this_tick = 0
        while (
            rt.boarding_queue
            and elev.can_board()
            and boarded_this_tick < PASSENGERS_BOARDING_PER_TICK
        ):
            passenger = rt.boarding_queue.pop(0)
            # Verify passenger is still eligible (hasn't been picked up
            # by another elevator in a multi-elevator scenario)
            if (
                passenger.state != PassengerState.WAITING
                or passenger not in self.building.waiting_passengers
            ):
                continue
            self.building.remove_waiting_passenger(passenger.id)
            elev.begin_boarding(passenger, current_tick)
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.PASSENGER_BOARDING,
                elevator_id=elev.id,
                floor=elev.current_floor,
                passenger_id=passenger.id,
            ))
            boarded_this_tick += 1

        # If elevator is full, clear remaining boarding queue.
        # These passengers were never removed from building.waiting_passengers,
        # so they remain safely waiting.
        if not elev.can_board() and rt.boarding_queue:
            rt.boarding_queue.clear()

        # Step 4: Decrement dwell timer
        if rt.dwell_remaining > 0:
            rt.dwell_remaining -= 1

        # Step 5: If no more boarding work and dwell expired → close doors
        has_boarding_in_progress = any(
            p.state == PassengerState.BOARDING for p in elev.passengers
        )
        if (
            not rt.boarding_queue
            and not has_boarding_in_progress
            and rt.dwell_remaining <= 0
        ):
            elev.close_doors()
            rt.door_timer = DOOR_CLOSING_TICKS
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.DOORS_CLOSING,
                elevator_id=elev.id,
                floor=elev.current_floor,
            ))

    def _process_door_closing(
        self,
        elev: Elevator,
        rt: _ElevatorRuntime,
        current_tick: int,
        events: list[SimulationEvent],
    ) -> None:
        """CLOSING phase: count down timer, then transition to CLOSED."""
        rt.door_timer -= 1
        if rt.door_timer <= 0:
            elev.finish_closing()
            events.append(SimulationEvent(
                tick=current_tick,
                event_type=EventType.DOORS_CLOSED,
                elevator_id=elev.id,
                floor=elev.current_floor,
            ))

            # Remove the completed stop (must be stops[0])
            if elev.stops and elev.stops[0] == elev.current_floor:
                elev.stops.pop(0)
            else:
                raise RuntimeError(
                    f"Engine state inconsistency: expected stops[0] == "
                    f"{elev.current_floor}, got stops = {elev.stops}"
                )

            # Determine next action
            if elev.stops:
                next_stop = elev.stops[0]
                if next_stop > elev.current_floor:
                    elev.direction = Direction.UP
                    elev.state = ElevatorState.MOVING
                    events.append(SimulationEvent(
                        tick=current_tick,
                        event_type=EventType.ELEVATOR_DEPARTED,
                        elevator_id=elev.id,
                        floor=elev.current_floor,
                        details=f"Heading {elev.direction.name} toward floor {next_stop}",
                    ))
                elif next_stop < elev.current_floor:
                    elev.direction = Direction.DOWN
                    elev.state = ElevatorState.MOVING
                    events.append(SimulationEvent(
                        tick=current_tick,
                        event_type=EventType.ELEVATOR_DEPARTED,
                        elevator_id=elev.id,
                        floor=elev.current_floor,
                        details=f"Heading {elev.direction.name} toward floor {next_stop}",
                    ))
                else:
                    # next_stop == current_floor: re-enter STOPPED,
                    # begin a new door cycle deterministically.
                    elev.state = ElevatorState.STOPPED
                    elev.open_doors()
                    rt.door_timer = DOOR_OPENING_TICKS
                    rt.discharged_this_stop = False
                    rt.boarding_queue = []
                    rt.dwell_remaining = DOOR_OPEN_DWELL_TICKS
                    events.append(SimulationEvent(
                        tick=current_tick,
                        event_type=EventType.ELEVATOR_STOPPED,
                        elevator_id=elev.id,
                        floor=elev.current_floor,
                    ))
                    events.append(SimulationEvent(
                        tick=current_tick,
                        event_type=EventType.DOORS_OPENING,
                        elevator_id=elev.id,
                        floor=elev.current_floor,
                    ))
            else:
                elev.direction = Direction.IDLE
                elev.state = ElevatorState.IDLE
                events.append(SimulationEvent(
                    tick=current_tick,
                    event_type=EventType.ELEVATOR_IDLE,
                    elevator_id=elev.id,
                    floor=elev.current_floor,
                ))
