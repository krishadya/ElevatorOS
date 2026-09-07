import type { HallDirection } from "../api/types";

interface HallCallButtonsProps {
  floor: number;
  disabled: boolean;
  activeDirections: HallDirection[];
  onHallCall: (floor: number, direction: HallDirection) => void;
}

export function HallCallButtons({
  floor,
  disabled,
  activeDirections,
  onHallCall,
}: HallCallButtonsProps) {
  return (
    <div className="hall-call-buttons" aria-label={`Hall calls for floor ${floor}`}>
      {floor < 10 && (
        <button
          className={`hall-call-button hall-call-up ${activeDirections.includes("UP") ? "is-active" : ""}`}
          type="button"
          aria-label={`Hall call UP at floor ${floor}`}
          disabled={disabled}
          onClick={() => onHallCall(floor, "UP")}
        >
          ↑
        </button>
      )}
      {floor > 1 && (
        <button
          className={`hall-call-button hall-call-down ${activeDirections.includes("DOWN") ? "is-active" : ""}`}
          type="button"
          aria-label={`Hall call DOWN at floor ${floor}`}
          disabled={disabled}
          onClick={() => onHallCall(floor, "DOWN")}
        >
          ↓
        </button>
      )}
    </div>
  );
}
