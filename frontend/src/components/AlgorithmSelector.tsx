import { useEffect, useRef, useState } from "react";

import type { AlgorithmName } from "../api/types";

interface AlgorithmSelectorProps {
  value: AlgorithmName;
  disabled: boolean;
  onChange: (algorithm: AlgorithmName) => void;
}

export function AlgorithmSelector({
  value,
  disabled,
  onChange,
}: AlgorithmSelectorProps) {
  const [isInfoOpen, setIsInfoOpen] = useState(false);
  const controlRef = useRef<HTMLDivElement>(null);
  const isFcfs = value === "fcfs";

  useEffect(() => {
    function closeOnOutsideClick(event: PointerEvent): void {
      if (!controlRef.current?.contains(event.target as Node)) {
        setIsInfoOpen(false);
      }
    }

    function closeOnEscape(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setIsInfoOpen(false);
      }
    }

    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  return (
    <div className="algorithm-control" ref={controlRef}>
      <label className="algorithm-selector">
        <span>Dispatch Algorithm</span>
        <select
          aria-label="Dispatch algorithm"
          disabled={disabled}
          onChange={(event) => onChange(event.target.value as AlgorithmName)}
          value={value}
        >
          <option value="fcfs">FCFS</option>
          <option value="nearest">Nearest Suitable Car</option>
        </select>
      </label>
      <button
        aria-controls="algorithm-info-popover"
        aria-expanded={isInfoOpen}
        aria-label="About the selected dispatch algorithm"
        className="algorithm-info-button"
        onClick={() => setIsInfoOpen((isOpen) => !isOpen)}
        type="button"
      >
        i
      </button>
      {isInfoOpen && (
        <section
          aria-label="Dispatch algorithm information"
          className="algorithm-info-popover"
          id="algorithm-info-popover"
          role="dialog"
        >
          <h2>{isFcfs ? "First-Come, First-Served (FCFS)" : "Nearest Suitable Car"}</h2>
          <p>
            {isFcfs
              ? "Handles hall calls in the order they were received. It does not optimize for distance or direction, making it a simple baseline for comparison."
              : "Chooses the elevator that best matches the caller's floor and requested direction. A car already moving toward the caller in the same direction is preferred over one moving the wrong way."}
          </p>
          <p className="algorithm-example">
            {isFcfs
              ? "Example: if Floor 8 calls before Floor 3, the Floor 8 request is processed first."
              : "Example: for a Floor 6 UP call, a car at Floor 4 moving UP may be chosen over one at Floor 5 moving DOWN."}
          </p>
        </section>
      )}
    </div>
  );
}
