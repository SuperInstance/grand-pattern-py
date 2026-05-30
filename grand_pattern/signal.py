"""Signal — routing, ports, algorithms, deadband, storm detection."""

import math
import time
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from .vibe import Vibe


class SignalType(Enum):
    VIBE = "vibe"
    CONTROL = "control"
    DATA = "data"
    ALERT = "alert"


class Signal:
    """A signal carrying a vibe payload."""

    def __init__(self, source: str, target: Optional[str], stype: SignalType,
                 payload: Optional[Vibe] = None, timestamp: Optional[float] = None,
                 priority: float = 0.5):
        self.source = source
        self.target = target
        self.stype = stype
        self.payload = payload or Vibe()
        self.timestamp = timestamp or time.time()
        self.priority = priority

    def __repr__(self) -> str:
        return f"Signal({self.source}->{self.target}, {self.stype.value})"


class Port:
    """Named input/output port on a room."""

    def __init__(self, name: str, is_output: bool = False):
        self.name = name
        self.is_output = is_output
        self.buffer: List[Signal] = []

    def push(self, signal: Signal):
        self.buffer.append(signal)

    def pop(self) -> Optional[Signal]:
        return self.buffer.pop(0) if self.buffer else None

    def flush(self) -> List[Signal]:
        out = self.buffer[:]
        self.buffer.clear()
        return out


class RouteAlgorithm(Enum):
    DIRECT = "direct"
    BUFFERED = "buffered"
    CORRELATED = "correlated"
    ON_CHANGE = "on_change"
    SAMPLED = "sampled"
    ADAPTIVE = "adaptive"


class Route:
    """A connection from one port to another."""

    def __init__(self, from_port: str, to_port: str, algorithm: RouteAlgorithm = RouteAlgorithm.DIRECT,
                 deadband: float = 0.0, sample_rate: int = 1):
        self.from_port = from_port
        self.to_port = to_port
        self.algorithm = algorithm
        self.deadband = deadband
        self.sample_rate = sample_rate
        self.last_value: Optional[Vibe] = None
        self.last_time: float = 0.0
        self.tick_count = 0
        self.correlation_id: Optional[str] = None

    def should_send(self, value: Vibe) -> bool:
        """Check if signal should pass based on algorithm."""
        self.tick_count += 1

        if self.algorithm == RouteAlgorithm.DIRECT:
            return True

        if self.algorithm == RouteAlgorithm.BUFFERED:
            return True  # always accept, consumer pops at own pace

        if self.algorithm == RouteAlgorithm.ON_CHANGE:
            if self.last_value is None:
                return True
            return self.last_value.distance(value) > self.deadband

        if self.algorithm == RouteAlgorithm.SAMPLED:
            return self.tick_count % self.sample_rate == 0

        if self.algorithm == RouteAlgorithm.CORRELATED:
            return True  # correlation checked at router level

        if self.algorithm == RouteAlgorithm.ADAPTIVE:
            if self.last_value is None:
                return True
            delta = self.last_value.distance(value)
            return delta > self.deadband or (self.tick_count % max(1, int(1.0 / max(0.01, delta + 0.01))) == 0)

        return True

    def record_send(self, value: Vibe):
        self.last_value = value.copy()
        self.last_time = time.time()


class Router:
    """Routes signals between ports using various algorithms."""

    def __init__(self):
        self.ports: Dict[str, Port] = {}
        self.routes: List[Route] = []
        self.signals_sent: int = 0
        self.signals_dropped: int = 0
        self._storm_window: List[float] = []

    def add_port(self, name: str, is_output: bool = False) -> Port:
        port = Port(name, is_output)
        self.ports[name] = port
        return port

    def add_route(self, from_port: str, to_port: str,
                  algorithm: RouteAlgorithm = RouteAlgorithm.DIRECT,
                  deadband: float = 0.0, sample_rate: int = 1) -> Route:
        route = Route(from_port, to_port, algorithm, deadband, sample_rate)
        self.routes.append(route)
        return route

    def send(self, signal: Signal) -> int:
        """Send a signal through matching routes. Returns count delivered."""
        delivered = 0
        for route in self.routes:
            if route.from_port != signal.source:
                continue
            if signal.target and route.to_port != signal.target:
                continue
            if not route.should_send(signal.payload):
                self.signals_dropped += 1
                continue
            target_port = self.ports.get(route.to_port)
            if target_port:
                target_port.push(signal)
                route.record_send(signal.payload)
                delivered += 1
                self.signals_sent += 1
        return delivered

    def receive(self, port_name: str) -> List[Signal]:
        port = self.ports.get(port_name)
        if not port:
            return []
        return port.flush()

    def broadcast(self, source: str, signal: Signal) -> int:
        """Broadcast from a source port to all connected routes."""
        signal.source = source
        return self.send(signal)

    def find_path(self, from_port: str, to_port: str) -> List[str]:
        """Find a path from one port to another through routes (BFS)."""
        if from_port == to_port:
            return [from_port]
        adj: Dict[str, List[str]] = {}
        for r in self.routes:
            adj.setdefault(r.from_port, []).append(r.to_port)
        visited = {from_port}
        queue = [[from_port]]
        while queue:
            path = queue.pop(0)
            node = path[-1]
            for neighbor in adj.get(node, []):
                if neighbor == to_port:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return []

    def detect_storm(self, window_seconds: float = 1.0, threshold: int = 100) -> bool:
        """Detect if too many signals were sent in a time window."""
        now = time.time()
        self._storm_window.append(now)
        cutoff = now - window_seconds
        self._storm_window = [t for t in self._storm_window if t > cutoff]
        return len(self._storm_window) > threshold
