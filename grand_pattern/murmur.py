"""Murmur — gossip protocol for distributed vibe propagation."""

import time
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

from .vibe import Vibe


class MurmurLevel(IntEnum):
    NEIGHBOR = 0
    ZONE = 1
    FLEET = 2


class MurmurPacket:
    """A gossip packet carrying a vibe snapshot."""

    def __init__(self, source_id: str, vibe: Vibe, level: MurmurLevel = MurmurLevel.NEIGHBOR,
                 ttl: int = 5, hops: int = 0, timestamp: Optional[float] = None):
        self.source_id = source_id
        self.vibe = vibe.copy()
        self.level = level
        self.ttl = ttl
        self.hops = hops
        self.timestamp = timestamp or time.time()

    def is_expired(self) -> bool:
        return self.ttl <= 0 or (time.time() - self.timestamp > 60.0)

    def decay(self, factor: float = 0.9) -> "MurmurPacket":
        """Return a decayed copy (reduced TTL, incremented hops)."""
        return MurmurPacket(
            source_id=self.source_id,
            vibe=self.vibe,
            level=self.level,
            ttl=max(0, self.ttl - 1),
            hops=self.hops + 1,
            timestamp=self.timestamp,
        )


class Murmur:
    """Local murmur buffer — compress, decay, check expiry."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.buffer: Dict[str, MurmurPacket] = {}

    def ingest(self, packet: MurmurPacket):
        key = f"{packet.source_id}:{packet.level}"
        existing = self.buffer.get(key)
        if existing is None or packet.timestamp > existing.timestamp:
            self.buffer[key] = packet

    def compress(self, max_packets: int = 20) -> List[MurmurPacket]:
        """Return top-N packets by freshness, decayed."""
        packets = sorted(self.buffer.values(), key=lambda p: -p.timestamp)[:max_packets]
        return [p.decay() for p in packets]

    def decay_all(self):
        """Remove expired packets."""
        self.buffer = {k: v for k, v in self.buffer.items() if not v.is_expired()}

    def is_empty(self) -> bool:
        return len(self.buffer) == 0

    def summary(self) -> Dict[str, int]:
        levels = {}
        for p in self.buffer.values():
            name = MurmurLevel(p.level).name
            levels[name] = levels.get(name, 0) + 1
        return levels


class GossipRound:
    """One round of gossip — send, receive, collect garbage."""

    def __init__(self):
        self.sent: List[MurmurPacket] = []
        self.received: List[MurmurPacket] = []

    def send(self, murmur: Murmur, max_packets: int = 10) -> List[MurmurPacket]:
        """Prepare packets to send from a murmur buffer."""
        packets = murmur.compress(max_packets)
        self.sent.extend(packets)
        return packets

    def receive(self, murmur: Murmur, packets: List[MurmurPacket]):
        """Receive packets into a murmur buffer."""
        for p in packets:
            murmur.ingest(p)
        self.received.extend(packets)

    def collect_garbage(self, murmur: Murmur):
        murmur.decay_all()

    def summary(self) -> Dict:
        return {
            "sent": len(self.sent),
            "received": len(self.received),
        }
