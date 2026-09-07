from app.main import SimulationSession, HallCallInput, CarRequestInput, create_hall_call, create_car_request, reset, tick, get_state, select_algorithm, AlgorithmInput
from fastapi import Request
from pydantic import BaseModel
from app.simulation.engine import DoorState, ElevatorState

class MockApp:
    def __init__(self):
        self.state = type('State', (), {})()
        self.state.simulation = SimulationSession.create_default()

class MockRequest:
    def __init__(self):
        self.app = MockApp()

def run_tests():
    req = MockRequest()
    
    # Send elevator 1 to floor 5
    create_hall_call(HallCallInput(floor=5, direction="UP"), req)
    
    # Tick until elevator 1 arrives and doors are OPEN
    arrived = False
    for _ in range(50):
        tick(req)
        state = get_state(req)
        e1 = state['elevators'][0]
        if e1['current_floor'] == 5 and e1['door_state'] == 'OPEN':
            arrived = True
            break
            
    print(f"E1 arrived at 5 and OPEN: {arrived}")
    
    # Now create another hall call at floor 5 UP while doors are OPEN
    res = create_hall_call(HallCallInput(floor=5, direction="UP"), req)
    print("New call assigned to:", res['assignment']['elevator_id'])
    
    state = get_state(req)
    e1 = state['elevators'][0]
    e2 = state['elevators'][1]
    print(f"E1 stops: {e1['stops']}, state: {e1['state']}, door_state: {e1['door_state']}")
    print(f"E2 stops: {e2['stops']}, state: {e2['state']}")

    # Let's see what happens if we keep ticking
    print("Ticking...")
    for _ in range(20):
        tick(req)
        state = get_state(req)
        e1 = state['elevators'][0]
        # just print state transitions
        print(f"E1: stops: {e1['stops']}, floor: {e1['current_floor']}, state: {e1['state']}, door: {e1['door_state']}")

if __name__ == "__main__":
    run_tests()
