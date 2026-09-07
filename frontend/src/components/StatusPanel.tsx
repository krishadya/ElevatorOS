import type { SimulationState } from "../api/types";

interface StatusPanelProps {
  state: SimulationState;
}

function eventText(event: SimulationState["recent_events"][number]): string {
  const floor = event.floor === null ? "" : ` at floor ${event.floor}`;
  return `Tick ${event.tick}: ${event.elevator_id} ${event.type.replaceAll("_", " ")}${floor}`;
}

function badgeClass(value: string): string {
  return `status-badge status-${value.toLowerCase()}`;
}

export function StatusPanel({ state }: StatusPanelProps) {
  return (
    <aside className="status-panel">
      <header className="status-panel-header">
        <div>
          <p>Live System</p>
          <h2>System Status</h2>
        </div>
        <div className="status-summary">
          <span>Tick {state.tick}</span>
          <span className="status-badge">{state.algorithm}</span>
        </div>
      </header>

      {state.elevators.map((elevator) => (
        <section className="elevator-status" key={elevator.id}>
          <div className="elevator-status-heading">
            <h3>{elevator.id}</h3>
            <div className="status-floor">
              <span>Floor</span>
              <strong>{String(elevator.current_floor).padStart(2, "0")}</strong>
            </div>
          </div>
          <dl>
            <div><dt>Direction</dt><dd><span className={badgeClass(elevator.direction)}>{elevator.direction}</span></dd></div>
            <div><dt>State</dt><dd><span className={badgeClass(elevator.state)}>{elevator.state}</span></dd></div>
            <div><dt>Doors</dt><dd><span className={badgeClass(elevator.door_state)}>{elevator.door_state}</span></dd></div>
            <div><dt>Stops</dt><dd>{elevator.stops.length ? elevator.stops.join(" → ") : "None"}</dd></div>
          </dl>
        </section>
      ))}

      <section className="active-calls-section">
        <h3>Active Hall Calls</h3>
        {state.active_hall_calls.length === 0 ? (
          <p className="empty-state">No active calls</p>
        ) : (
          <ul>
            {state.active_hall_calls.map((call) => (
              <li className="active-call-card" key={call.id}>
                <strong>
                  <span>{String(call.floor).padStart(2, "0")}</span>
                  <span>{call.direction === "UP" ? "↑" : "↓"}</span>
                </strong>
                <span>Assigned {call.assigned_elevator ?? "Unassigned"}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="event-feed">
        <h3>Recent Events</h3>
        {state.recent_events.length === 0 ? (
          <p className="empty-state">No recent events</p>
        ) : (
          <ul>
            {state.recent_events.map((event, index) => (
              <li key={`${event.tick}-${event.elevator_id}-${event.type}-${index}`}>
                <span className="event-tick">T{event.tick}</span>
                <span>{eventText(event)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
