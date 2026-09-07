import { useEffect, useRef, useState } from "react";

import * as api from "./api/client";
import type { AlgorithmName, HallDirection, SimulationState } from "./api/types";
import { AlgorithmSelector } from "./components/AlgorithmSelector";
import { Building } from "./components/Building";
import { CarPanel } from "./components/CarPanel";
import { SimulationControls } from "./components/SimulationControls";
import { StatusPanel } from "./components/StatusPanel";

const PLAY_INTERVAL_MS = 750;

export default function App() {
  const [state, setState] = useState<SimulationState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState(false);
  const requestInFlight = useRef(false);

  async function runRequest(operation: () => Promise<void>): Promise<void> {
    if (requestInFlight.current) {
      return;
    }

    requestInFlight.current = true;
    setLoading(true);
    setError(null);
    try {
      await operation();
    } catch (caughtError) {
      setPlaying(false);
      setError(caughtError instanceof Error ? caughtError.message : "API request failed.");
    } finally {
      requestInFlight.current = false;
      setLoading(false);
    }
  }

  function refreshState(): Promise<void> {
    return api.getState().then(setState);
  }

  function handleStep(): Promise<void> {
    return runRequest(async () => {
      setState(await api.tick());
    });
  }

  function handleHallCall(floor: number, direction: HallDirection): void {
    void runRequest(async () => {
      await api.createHallCall(floor, direction);
      await refreshState();
    });
  }

  function handleDestination(elevatorId: string, floor: number): void {
    void runRequest(async () => {
      await api.createCarRequest(elevatorId, floor);
      await refreshState();
    });
  }

  function handleAlgorithmChange(algorithm: AlgorithmName): void {
    void runRequest(async () => {
      await api.setAlgorithm(algorithm);
      await refreshState();
    });
  }

  function handleReset(): void {
    setPlaying(false);
    void runRequest(async () => {
      setState(await api.reset());
    });
  }

  useEffect(() => {
    void runRequest(refreshState);
  }, []);

  useEffect(() => {
    if (!playing) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      void handleStep();
    }, PLAY_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [playing]);

  if (loading && state === null) {
    return <main className="app-shell">Loading simulation…</main>;
  }

  if (state === null) {
    return (
      <main className="app-shell">
        <p>Unable to load the simulation.</p>
        {error && <p className="error-message" role="alert">{error}</p>}
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="simulator-toolbar">
        <div className="toolbar-brand">
          <h1>ElevatorOS</h1>
          <p>Deterministic elevator simulation</p>
        </div>
        <div className="toolbar-actions">
          <AlgorithmSelector
            disabled={loading}
            onChange={handleAlgorithmChange}
            value={state.algorithm}
          />
          <SimulationControls
            disabled={loading}
            onPause={() => setPlaying(false)}
            onPlay={() => setPlaying(true)}
            onReset={handleReset}
            onStep={() => void handleStep()}
            playing={playing}
          />
        </div>
      </header>

      {error && <p className="error-message" role="alert">{error}</p>}

      <div className="simulator-layout">
        <div>
          <Building
            activeCalls={state.active_hall_calls}
            disabled={loading}
            elevators={state.elevators}
            onHallCall={handleHallCall}
          />
          <CarPanel
            disabled={loading}
            elevators={state.elevators}
            onDestination={handleDestination}
          />
        </div>
        <StatusPanel state={state} />
      </div>
    </main>
  );
}
