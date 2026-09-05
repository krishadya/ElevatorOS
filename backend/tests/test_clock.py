"""Tests for the SimulationClock."""

import pytest

from app.simulation.clock import SimulationClock


class TestClockCreation:
    """Verify clock construction and defaults."""

    def test_default_creation(self):
        c = SimulationClock()
        assert c.current_tick == 0
        assert c.tick_step == 1
        assert c.time == 0

    def test_custom_tick_step(self):
        c = SimulationClock(tick_step=5)
        assert c.tick_step == 5

    def test_invalid_tick_step(self):
        with pytest.raises(ValueError, match="tick_step"):
            SimulationClock(tick_step=0)


class TestClockProgression:
    """Verify deterministic tick advancement."""

    def test_single_tick(self):
        c = SimulationClock()
        result = c.tick()
        assert result == 1
        assert c.current_tick == 1

    def test_multiple_single_ticks(self):
        c = SimulationClock()
        for i in range(1, 6):
            c.tick()
        assert c.current_tick == 5

    def test_multi_step_tick(self):
        c = SimulationClock()
        result = c.tick(steps=10)
        assert result == 10
        assert c.current_tick == 10

    def test_custom_tick_step_advancement(self):
        c = SimulationClock(tick_step=5)
        c.tick()
        assert c.current_tick == 5
        c.tick()
        assert c.current_tick == 10

    def test_custom_tick_step_with_multiple_steps(self):
        c = SimulationClock(tick_step=3)
        c.tick(steps=4)
        assert c.current_tick == 12  # 3 * 4

    def test_invalid_steps_raises(self):
        c = SimulationClock()
        with pytest.raises(ValueError, match="steps"):
            c.tick(steps=0)

    def test_time_property_matches_current_tick(self):
        c = SimulationClock()
        c.tick(steps=7)
        assert c.time == c.current_tick == 7


class TestClockReproducibility:
    """Verify that two clocks with the same inputs produce identical results."""

    def test_two_clocks_produce_same_results(self):
        c1 = SimulationClock(tick_step=2)
        c2 = SimulationClock(tick_step=2)

        for _ in range(100):
            c1.tick()
            c2.tick()

        assert c1.current_tick == c2.current_tick
        assert c1.time == c2.time

    def test_reset_enables_exact_replay(self):
        c = SimulationClock(tick_step=3)

        # First run
        for _ in range(50):
            c.tick()
        first_run_result = c.current_tick

        # Reset and replay
        c.reset()
        assert c.current_tick == 0

        for _ in range(50):
            c.tick()
        second_run_result = c.current_tick

        assert first_run_result == second_run_result

    def test_reset_to_zero(self):
        c = SimulationClock()
        c.tick(steps=100)
        assert c.current_tick == 100
        c.reset()
        assert c.current_tick == 0
        assert c.time == 0
