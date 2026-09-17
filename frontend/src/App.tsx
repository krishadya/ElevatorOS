import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "./api/client";
import type { AlgorithmName, HallDirection, SimulationState } from "./api/types";
import { AlgorithmSelector } from "./components/AlgorithmSelector";
import { Building } from "./components/Building";
import { CarPanel } from "./components/CarPanel";
import { LoadingScreen } from "./components/LoadingScreen";
import { SimulationControls } from "./components/SimulationControls";
import { StatusPanel } from "./components/StatusPanel";

const PLAY_INTERVAL_MS = 750;
const INITIAL_RETRY_DELAY_MS = 4_000;
const MAX_INITIAL_CONNECTION_ATTEMPTS = 16;

export default function App() {
  const [state, setState] = useState<SimulationState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [initialConnectionFailed, setInitialConnectionFailed] = useState(false);
  const [connectionCycle, setConnectionCycle] = useState(0);
  const requestInFlight = useRef(false);
  const initialConnectionInFlight = useRef(false);
  const initialConnectionAttempts = useRef(0);
  const initialRetryTimer = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const isMounted = useRef(true);

  const connectInitialState = useCallback((resetAttempts = false): void => {
    if (resetAttempts) {
      initialConnectionAttempts.current = 0;
    }
    if (initialConnectionInFlight.current) {
      return;
    }

    initialConnectionInFlight.current = true;
    setInitialConnectionFailed(false);
    setLoading(true);

    void api.getState()
      .then((initialState) => {
        if (!isMounted.current) {
          return;
        }
        initialConnectionAttempts.current = 0;
        setState(initialState);
        setLoading(false);
      })
      .catch(() => {
        if (!isMounted.current) {
          return;
        }
        initialConnectionAttempts.current += 1;
        if (initialConnectionAttempts.current >= MAX_INITIAL_CONNECTION_ATTEMPTS) {
          setInitialConnectionFailed(true);
          setLoading(false);
          return;
        }

        initialRetryTimer.current = window.setTimeout(
          () => connectInitialState(),
          INITIAL_RETRY_DELAY_MS,
        );
      })
      .finally(() => {
        initialConnectionInFlight.current = false;
      });
  }, []);

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
    isMounted.current = true;
    connectInitialState();

    return () => {
      isMounted.current = false;
      if (initialRetryTimer.current !== null) {
        window.clearTimeout(initialRetryTimer.current);
      }
    };
  }, [connectInitialState]);

  useEffect(() => {
    if (!playing) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      void handleStep();
    }, PLAY_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [playing]);

  function handleInitialRetry(): void {
    if (initialRetryTimer.current !== null) {
      window.clearTimeout(initialRetryTimer.current);
      initialRetryTimer.current = null;
    }
    setConnectionCycle((cycle) => cycle + 1);
    connectInitialState(true);
  }

  if (state === null) {
    return (
      <LoadingScreen
        connectionCycle={connectionCycle}
        failed={initialConnectionFailed}
        onRetry={handleInitialRetry}
      />
    );
  }

  return (
    <main className="app-shell simulator-shell">
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
