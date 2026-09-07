import type { HallCall, HallDirection, ElevatorState } from "../api/types";
import { ElevatorShaft } from "./ElevatorShaft";
import { Floor } from "./Floor";

interface BuildingProps {
  elevators: ElevatorState[];
  activeCalls: HallCall[];
  disabled: boolean;
  onHallCall: (floor: number, direction: HallDirection) => void;
}

const floors = Array.from({ length: 10 }, (_, index) => 10 - index);

export function Building({
  elevators,
  activeCalls,
  disabled,
  onHallCall,
}: BuildingProps) {
  return (
    <section className="building" aria-label="Building visualizer">
      <div className="floor-column">
        <h2>Building</h2>
        {floors.map((floor) => (
          <Floor
            activeCalls={activeCalls.filter((call) => call.floor === floor)}
            disabled={disabled}
            floor={floor}
            key={floor}
            onHallCall={onHallCall}
          />
        ))}
      </div>
      {elevators.map((elevator) => (
        <ElevatorShaft elevator={elevator} floors={floors} key={elevator.id} />
      ))}
    </section>
  );
}
