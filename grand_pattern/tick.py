"""Tick — temporal scheduling, tempo adaptation, countdown events."""

import time
from typing import Callable, List, Optional


class Tick:
    """A single tick event."""

    def __init__(self, tick_id: str, timestamp: Optional[float] = None):
        self.tick_id = tick_id
        self.timestamp = timestamp or time.time()

    def __repr__(self) -> str:
        return f"Tick({self.tick_id}, {self.timestamp:.2f})"


class TickSchedule:
    """Uniform or swing tick scheduler."""

    def __init__(self, tick_interval: float = 1.0, swing_offset: float = 0.0):
        self.tick_interval = max(0.01, tick_interval)
        self.swing_offset = swing_offset
        self.last_tick_time: Optional[float] = None
        self.tick_count = 0

    def next_tick(self) -> Tick:
        """Get the next tick, advancing the schedule."""
        now = time.time()
        if self.last_tick_time is None:
            self.last_tick_time = now
        else:
            swing = self.swing_offset if self.tick_count % 2 == 0 else -self.swing_offset
            self.last_tick_time += self.tick_interval + swing
            if self.last_tick_time < now:
                self.last_tick_time = now

        self.tick_count += 1
        return Tick(f"tick-{self.tick_count}", self.last_tick_time)


class Tempo:
    """Adaptive tempo — speeds up or slows down based on energy."""

    def __init__(self, bpm: float = 120.0, min_bpm: float = 30.0, max_bpm: float = 300.0):
        self.bpm = bpm
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm

    def adapt(self, energy: float) -> "Tempo":
        """Adapt BPM based on energy [0, 1]. Higher energy → faster."""
        target = self.min_bpm + (self.max_bpm - self.min_bpm) * max(0.0, min(1.0, energy))
        # Smooth toward target
        self.bpm = self.bpm * 0.8 + target * 0.2
        return self

    def clamp(self) -> "Tempo":
        self.bpm = max(self.min_bpm, min(self.max_bpm, self.bpm))
        return self

    def interval(self) -> float:
        """Tick interval in seconds."""
        return 60.0 / self.bpm


class TMinusEvent:
    """Countdown to a future tick."""

    def __init__(self, target_tick: int, on_ready: Optional[Callable] = None):
        self.target_tick = target_tick
        self.on_ready = on_ready
        self.current_tick = 0

    def tick(self):
        """Advance one tick. Returns True when ready."""
        self.current_tick += 1
        return self.is_ready()

    def is_ready(self) -> bool:
        ready = self.current_tick >= self.target_tick
        if ready and self.on_ready:
            self.on_ready()
        return ready
