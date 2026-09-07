import type { HallCall, HallDirection } from "../api/types";
import { HallCallButtons } from "./HallCallButtons";

interface FloorProps {
  floor: number;
  activeCalls: HallCall[];
  disabled: boolean;
  onHallCall: (floor: number, direction: HallDirection) => void;
}

export function Floor({ floor, activeCalls, disabled, onHallCall }: FloorProps) {
  return (
    <div className={`floor-row ${activeCalls.length ? "has-active-call" : ""}`}>
      <strong className="floor-label">
        <span className="sr-only">Floor {floor}</span>
        <span aria-hidden="true" className="floor-label-prefix">Floor</span>
        <span aria-hidden="true" className="floor-label-number">{String(floor).padStart(2, "0")}</span>
      </strong>
      <HallCallButtons
        activeDirections={activeCalls.map((call) => call.direction)}
        floor={floor}
        disabled={disabled}
        onHallCall={onHallCall}
      />
      <div className="active-call-markers">
        {activeCalls.map((call) => (
          <span key={call.id} className="active-call">
            <span>{call.direction === "UP" ? "↑" : "↓"}</span>
            <span>{call.assigned_elevator ?? "Unassigned"}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
