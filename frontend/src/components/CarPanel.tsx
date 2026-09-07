import type { ElevatorState } from "../api/types";

interface CarPanelProps {
  elevators: ElevatorState[];
  disabled: boolean;
  onDestination: (elevatorId: string, floor: number) => void;
}

const floors = Array.from({ length: 10 }, (_, index) => index + 1);

export function CarPanel({ elevators, disabled, onDestination }: CarPanelProps) {
  const openElevators = elevators.filter(
    (elevator) => elevator.state === "STOPPED" && elevator.door_state === "OPEN",
  );

  if (openElevators.length === 0) {
    return null;
  }

  return (
    <section className="car-panel" aria-label="Inside elevator destination controls">
      {openElevators.map((elevator) => (
        <div className="destination-panel" key={elevator.id}>
          <div>
            <p className="panel-kicker">Inside Elevator</p>
            <h2>{elevator.id} — Select Destination</h2>
          </div>
          <div className="destination-buttons">
            {floors.map((floor) => (
              <button
                aria-label={`${elevator.id} destination floor ${floor}`}
                disabled={disabled}
                key={floor}
                onClick={() => onDestination(elevator.id, floor)}
                type="button"
              >
                {floor}
              </button>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
