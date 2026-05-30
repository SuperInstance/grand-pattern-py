"""Jepa — perception / prediction / surprise with vector databases."""

import math
import time
from typing import List, Optional, Tuple

from .vibe import Vibe


class VectorDb:
    """Simple in-memory vector database."""

    def __init__(self):
        self.entries: List[Tuple[Vibe, float]] = []

    def insert(self, vibe: Vibe, ts: Optional[float] = None):
        self.entries.append((vibe.copy(), ts or time.time()))

    def average(self) -> Vibe:
        if not self.entries:
            return Vibe()
        avg = [0.0] * 16
        for v, _ in self.entries:
            for i in range(16):
                avg[i] += v.dims[i]
        n = len(self.entries)
        return Vibe([a / n for a in avg])

    def recent(self, n: int) -> List[Vibe]:
        return [v.copy() for v, _ in self.entries[-n:]]

    def size(self) -> int:
        return len(self.entries)


class Jepa:
    """Joint-Embedding Predictive Architecture — perceive, predict, surprise."""

    def __init__(self, history_len: int = 10, conservation_threshold: float = 0.3):
        self.perception_db = VectorDb()
        self.prediction_db = VectorDb()
        self.history_len = history_len
        self.conservation_threshold = conservation_threshold

    def perceive(self, vibe: Vibe):
        """Record an observed vibe."""
        self.perception_db.insert(vibe)

    def predict(self) -> Vibe:
        """Predict the next vibe as average of recent perceptions."""
        recent = self.perception_db.recent(self.history_len)
        if not recent:
            return Vibe()
        avg = [0.0] * 16
        for v in recent:
            for i in range(16):
                avg[i] += v.dims[i]
        n = len(recent)
        return Vibe([a / n for a in avg])

    def record_prediction(self, vibe: Optional[Vibe] = None):
        """Record a prediction (default: current predict())."""
        self.prediction_db.insert(vibe or self.predict())

    def surprise(self, observed: Vibe) -> float:
        """Cosine distance between predicted and observed. 0 = expected, 1 = max surprise."""
        pred = self.predict()
        sim = pred.groove_lock(observed)
        return 1.0 - max(0.0, min(1.0, sim))

    def check_conservation(self) -> float:
        """Check if average perception ≈ average prediction (energy conservation)."""
        if self.perception_db.size() == 0 or self.prediction_db.size() == 0:
            return 0.0
        p_avg = self.perception_db.average()
        r_avg = self.prediction_db.average()
        return p_avg.distance(r_avg)

    def gc(self, max_entries: int = 100):
        """Garbage collect — trim old entries."""
        for db in (self.perception_db, self.prediction_db):
            if db.size() > max_entries:
                db.entries = db.entries[-max_entries:]
