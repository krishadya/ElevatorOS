interface SimulationControlsProps {
  playing: boolean;
  disabled: boolean;
  onPlay: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
}

export function SimulationControls({
  playing,
  disabled,
  onPlay,
  onPause,
  onStep,
  onReset,
}: SimulationControlsProps) {
  return (
    <div className="simulation-controls" aria-label="Simulation controls">
      <span className={`playback-status ${playing ? "is-playing" : "is-paused"}`}>
        {playing ? "Playing" : "Paused"}
      </span>
      <div className="control-buttons">
        <button className="control-primary" disabled={disabled || playing} onClick={onPlay} type="button">
          Play
        </button>
        <button disabled={!playing} onClick={onPause} type="button">
          Pause
        </button>
        <button disabled={disabled} onClick={onStep} type="button">
          Step
        </button>
        <button className="control-reset" disabled={disabled} onClick={onReset} type="button">
          Reset
        </button>
      </div>
    </div>
  );
}
