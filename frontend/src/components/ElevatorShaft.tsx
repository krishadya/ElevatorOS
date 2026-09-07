import type { ElevatorState } from "../api/types";

interface ElevatorShaftProps {
  elevator: ElevatorState;
  floors: number[];
}

const FLOOR_HEIGHT_PX = 60;

export function ElevatorShaft({ elevator, floors }: ElevatorShaftProps) {
  const offset = (floors[0] - elevator.current_floor) * FLOOR_HEIGHT_PX;
  const directionIndicator = elevator.direction === "UP" ? "↑" : elevator.direction === "DOWN" ? "↓" : "•";

  return (
    <section className="elevator-shaft" aria-label={`${elevator.id} shaft`}>
      <header className="shaft-header">
        <span className="shaft-title">
          <strong>{elevator.id}</strong>
          <span>{elevator.state}</span>
        </span>
        <span className="shaft-indicator" aria-label={`Floor ${elevator.current_floor}, ${elevator.direction}`}>
          <span aria-hidden="true">{directionIndicator}</span>
          <strong>{String(elevator.current_floor).padStart(2, "0")}</strong>
        </span>
      </header>
      <div className="shaft-track">
        {floors.map((floor) => (
          <div
            className="shaft-floor"
            data-testid={`${elevator.id}-floor-${floor}`}
            key={floor}
          />
        ))}
        <div
          aria-label={`${elevator.id} at floor ${elevator.current_floor}, doors ${elevator.door_state}`}
          className={`elevator-car door-${elevator.door_state.toLowerCase()}`}
          style={{ transform: `translateY(${offset}px)` }}
        >
          <div className="car-label">
            <strong>{elevator.id}</strong>
            <span>{elevator.state}</span>
          </div>
          <div className="door-frame" aria-hidden="true">
            <span className="door-panel door-panel-left" />
            <span className="door-panel door-panel-right" />
          </div>
        </div>
      </div>
    </section>
  );
}
