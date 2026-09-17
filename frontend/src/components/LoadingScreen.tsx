import { useEffect, useState } from "react";

interface LoadingScreenProps {
  connectionCycle: number;
  failed: boolean;
  onRetry: () => void;
}

type WakeUpMessage = "delayed" | "extended" | null;

export function LoadingScreen({
  connectionCycle,
  failed,
  onRetry,
}: LoadingScreenProps) {
  const [wakeUpMessage, setWakeUpMessage] = useState<WakeUpMessage>(null);

  useEffect(() => {
    setWakeUpMessage(null);
    const delayedMessageTimer = window.setTimeout(
      () => setWakeUpMessage("delayed"),
      5_000,
    );
    const extendedMessageTimer = window.setTimeout(
      () => setWakeUpMessage("extended"),
      20_000,
    );

    return () => {
      window.clearTimeout(delayedMessageTimer);
      window.clearTimeout(extendedMessageTimer);
    };
  }, [connectionCycle]);

  return (
    <main className="initial-loading-screen">
      <section className="loading-console" aria-live="polite">
        <p className="loading-brand">ElevatorOS</p>
        <div className="loading-shaft" aria-hidden="true">
          <span className="loading-floor-line loading-floor-line-one" />
          <span className="loading-floor-line loading-floor-line-two" />
          <span className="loading-floor-line loading-floor-line-three" />
          <span className="loading-floor-line loading-floor-line-four" />
          <span className="loading-cabin">
            <span />
            <span />
          </span>
        </div>

        {failed ? (
          <div className="loading-error" role="alert">
            <h1>Couldn&apos;t connect to the simulator.</h1>
            <p>Check your connection, then try the simulation engine again.</p>
            <button type="button" onClick={onRetry}>
              Try Again
            </button>
          </div>
        ) : (
          <>
            <h1>Starting simulation...</h1>
            <p className="loading-primary-message">
              Connecting to the simulation engine
            </p>
            {wakeUpMessage === "delayed" && (
              <p className="loading-secondary-message">
                The backend may take a few seconds to wake up after being idle.
              </p>
            )}
            {wakeUpMessage === "extended" && (
              <p className="loading-secondary-message">
                Still waking up. Free hosting can take up to a minute after inactivity.
              </p>
            )}
          </>
        )}
      </section>
    </main>
  );
}
