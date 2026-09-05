"""Deterministic simulation clock for ElevatorOS.

The clock is purely tick-based with no dependency on wall-clock time.
Advancing the clock is always explicit, making simulation runs
fully reproducible regardless of execution speed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimulationClock:
    """A deterministic, tick-based simulation clock.

    Attributes:
        current_tick: The current simulation tick (starts at 0).
        tick_step: How many time-units each tick advances. Can be
            adjusted to support speed multipliers in future milestones.

    Design notes:
        - No wall-clock dependency: time only advances via ``tick()``.
        - Reproducible: two clocks with the same ``tick_step`` and
          the same number of ``tick()`` calls will always agree.
        - A seeded RNG can later be attached to the clock to drive
          stochastic passenger generation while preserving determinism.
    """

    current_tick: int = 0
    tick_step: int = 1

    def __post_init__(self) -> None:
        if self.tick_step < 1:
            raise ValueError(
                f"tick_step must be >= 1, got {self.tick_step}"
            )

    def tick(self, steps: int = 1) -> int:
        """Advance the clock by ``steps`` tick increments.

        Args:
            steps: Number of tick increments to advance (default 1).
                Each increment adds ``tick_step`` time-units.

        Returns:
            The new current_tick value after advancing.

        Raises:
            ValueError: If steps < 1.
        """
        if steps < 1:
            raise ValueError(f"steps must be >= 1, got {steps}")
        self.current_tick += self.tick_step * steps
        return self.current_tick

    def reset(self) -> None:
        """Reset the clock to tick 0 for reproducible reruns."""
        self.current_tick = 0

    @property
    def time(self) -> int:
        """Current simulation time (alias for current_tick)."""
        return self.current_tick
