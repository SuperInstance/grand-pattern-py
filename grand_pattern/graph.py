"""CellGraph — composes all primitives into a cellular graph."""

import math
from typing import Dict, List, Optional, Set, Tuple

from .vibe import Vibe
from .room import Room
from .murmur import GossipRound, MurmurLevel, MurmurPacket
from .tick import TickSchedule, Tempo, TMinusEvent
from .signal import Router, RouteAlgorithm, Signal, SignalType


class CellGraph:
    """Cellular graph — rooms connected by edges, gossiping, routing signals."""

    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.edges: Dict[str, Set[str]] = {}  # room_id -> set of neighbor room_ids
        self.router = Router()
        self.schedule = TickSchedule()
        self.tempo = Tempo()
        self._tick_count = 0

    def add_room(self, room_id: str, initial_vibe: Optional[Vibe] = None) -> Room:
        room = Room(room_id, initial_vibe)
        self.rooms[room_id] = room
        self.edges.setdefault(room_id, set())
        # Create router ports
        self.router.add_port(f"{room_id}:in")
        self.router.add_port(f"{room_id}:out", is_output=True)
        return room

    def add_edge(self, room_a: str, room_b: str, bidirectional: bool = True):
        self.edges.setdefault(room_a, set()).add(room_b)
        if bidirectional:
            self.edges.setdefault(room_b, set()).add(room_a)
        # Add default route
        self.router.add_route(f"{room_a}:out", f"{room_b}:in",
                              RouteAlgorithm.DIRECT)

    def tick(self) -> int:
        """Advance all rooms by one tick."""
        self._tick_count += 1
        for room in self.rooms.values():
            room.tick()
        return self._tick_count

    def gossip(self, level: MurmurLevel = MurmurLevel.NEIGHBOR, ttl: int = 5):
        """One round of gossip between connected rooms."""
        round_ = GossipRound()
        # Each room sends to neighbors
        for room_id, neighbors in self.edges.items():
            room = self.rooms.get(room_id)
            if not room:
                continue
            packet = room.gossip_out(level, ttl)
            for nid in neighbors:
                n_room = self.rooms.get(nid)
                if n_room:
                    n_room.gossip_in(packet)
                    round_.received.append(packet)
            round_.sent.append(packet)
        return round_.summary()

    def route_signals(self):
        """Route all pending signals."""
        for room in self.rooms.values():
            sig = Signal(room.room_id, None, SignalType.VIBE, room.vibe)
            self.router.send(sig)

    def fleet_vibe(self) -> Vibe:
        """Average vibe across all rooms."""
        if not self.rooms:
            return Vibe()
        vibes = [r.vibe for r in self.rooms.values()]
        avg = [0.0] * 16
        for v in vibes:
            for i in range(16):
                avg[i] += v.dims[i]
        n = len(vibes)
        return Vibe([a / n for a in avg])

    def fleet_surprise(self) -> float:
        """Average surprise across all rooms."""
        if not self.rooms:
            return 0.0
        surprises = [r.surprise() for r in self.rooms.values()]
        return sum(surprises) / len(surprises)

    def detect_anomaly(self, threshold: float = 0.5) -> List[str]:
        """Find rooms with surprise above threshold."""
        anomalous = []
        for room_id, room in self.rooms.items():
            if room.surprise() > threshold:
                anomalous.append(room_id)
        return anomalous

    def conservation_report(self) -> Dict[str, float]:
        """Check energy conservation for each room."""
        report = {}
        for room_id, room in self.rooms.items():
            report[room_id] = room.jepa.check_conservation()
        return report

    def diffuse_all(self, coeff: float = 0.1):
        """Diffuse vibes across all edges."""
        new_vibes: Dict[str, Vibe] = {}
        for room_id, neighbors in self.edges.items():
            room = self.rooms[room_id]
            neighbor_rooms = [self.rooms[nid] for nid in neighbors if nid in self.rooms]
            new_vibes[room_id] = room.vibe.diffuse(
                [r.vibe for r in neighbor_rooms], coeff=coeff
            )
        for room_id, vibe in new_vibes.items():
            self.rooms[room_id].vibe = vibe

    def summary(self) -> Dict:
        return {
            "rooms": len(self.rooms),
            "edges": sum(len(n) for n in self.edges.values()) // 2 if self.edges else 0,
            "tick": self._tick_count,
            "fleet_vibe": self.fleet_vibe().qualitative_description(),
            "fleet_surprise": round(self.fleet_surprise(), 4),
            "anomalies": self.detect_anomaly(),
        }
