"""Room — composes Vibe + Jepa + Murmur into a single cell."""

from typing import Dict, List, Optional

from .vibe import Vibe
from .jepa import Jepa
from .murmur import Murmur, MurmurPacket, MurmurLevel


class Room:
    """A single cell in the Grand Pattern — composes vibe, jepa, murmur."""

    def __init__(self, room_id: str, initial_vibe: Optional[Vibe] = None):
        self.room_id = room_id
        self.vibe = initial_vibe or Vibe()
        self.jepa = Jepa()
        self.murmur = Murmur(room_id)

    def perceive(self, vibe: Optional[Vibe] = None):
        """Perceive a vibe (default: own vibe), feed to jepa."""
        v = vibe or self.vibe
        self.jepa.perceive(v)

    def predict(self) -> Vibe:
        return self.jepa.predict()

    def surprise(self, observed: Optional[Vibe] = None) -> float:
        v = observed or self.vibe
        return self.jepa.surprise(v)

    def gossip_out(self, level: MurmurLevel = MurmurLevel.NEIGHBOR,
                   ttl: int = 5) -> MurmurPacket:
        """Create a gossip packet about own vibe."""
        return MurmurPacket(self.room_id, self.vibe, level, ttl)

    def gossip_in(self, packet: MurmurPacket):
        """Receive a gossip packet."""
        self.murmur.ingest(packet)

    def diffuse(self, neighbors: List["Room"], coeff: float = 0.1):
        """Diffuse vibe toward neighbors."""
        if not neighbors:
            return
        neighbor_vibes = [r.vibe for r in neighbors]
        self.vibe = self.vibe.diffuse(neighbor_vibes, coeff=coeff)

    def tick(self):
        """One tick: perceive, record prediction."""
        self.perceive()
        self.jepa.record_prediction()

    def summary(self) -> Dict:
        return {
            "id": self.room_id,
            "vibe": self.vibe.qualitative_description(),
            "surprise": self.surprise(),
            "murmur": self.murmur.summary(),
        }
