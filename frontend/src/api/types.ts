export type HallDirection = "UP" | "DOWN";
export type AlgorithmName = "fcfs" | "nearest";

export interface ElevatorState {
  id: string;
  current_floor: number;
  direction: "UP" | "DOWN" | "IDLE";
  state: "IDLE" | "MOVING" | "STOPPED";
  door_state: "OPEN" | "CLOSED" | "OPENING" | "CLOSING";
  stops: number[];
}

export interface HallCall {
  id: string;
  floor: number;
  direction: HallDirection;
  assigned_elevator: string | null;
}

export interface SimulationEvent {
  tick: number;
  type: string;
  elevator_id: string;
  floor: number | null;
  passenger_id: string | null;
}

export interface SimulationState {
  tick: number;
  time: number;
  algorithm: AlgorithmName;
  elevators: ElevatorState[];
  active_hall_calls: HallCall[];
  recent_events: SimulationEvent[];
}

export interface HallCallResponse {
  hall_call: HallCall;
  assignment: { elevator_id: string };
}

export interface CarRequestResponse {
  car_request: {
    id: string;
    elevator_id: string;
    destination_floor: number;
  };
  stops: number[];
}
