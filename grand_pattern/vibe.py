"""Vibe — 16-dimensional emotional/spectral descriptor."""

import math
import re
from typing import Dict, List, Optional

DIM_NAMES = [
    "dark", "bright", "warm", "harsh", "dense", "sparse",
    "fast", "slow", "dry", "wet", "tight", "loose",
    "forward", "distant", "smooth", "rough",
]

# Keyword → (dim_index, sign)
_KEYWORD_MAP: Dict[str, tuple] = {
    "dark": (0, 1), "shadowy": (0, 1), "murky": (0, 1),
    "bright": (1, 1), "shiny": (1, 1), "luminous": (1, 1),
    "warm": (2, 1), "cozy": (2, 1), "hot": (2, 1),
    "harsh": (3, 1), "abrasive": (3, 1), "sharp": (3, 1),
    "dense": (4, 1), "thick": (4, 1), "heavy": (4, 1),
    "sparse": (5, 1), "thin": (5, 1), "light": (5, 1),
    "fast": (6, 1), "quick": (6, 1), "rapid": (6, 1),
    "slow": (7, 1), "languid": (7, 1), "dragging": (7, 1),
    "dry": (8, 1), "arid": (8, 1),
    "wet": (9, 1), "liquid": (9, 1), "lush": (9, 1),
    "tight": (10, 1), "compressed": (10, 1),
    "loose": (11, 1), "open": (11, 1), "free": (11, 1),
    "forward": (12, 1), "driving": (12, 1), "pushing": (12, 1),
    "distant": (13, 1), "far": (13, 1), "remote": (13, 1),
    "smooth": (14, 1), "silky": (14, 1),
    "rough": (15, 1), "gritty": (15, 1), "textured": (15, 1),
}

_DIM_DESCRIPTIONS = [
    (0, 1, "dark"), (0, -1, "bright"),
    (1, 1, "bright"), (1, -1, "dark"),
    (2, 1, "warm"), (2, -1, "cool"),
    (3, 1, "harsh"), (3, -1, "gentle"),
    (4, 1, "dense"), (4, -1, "sparse"),
    (5, 1, "sparse"), (5, -1, "dense"),
    (6, 1, "fast"), (6, -1, "slow"),
    (7, 1, "slow"), (7, -1, "fast"),
    (8, 1, "dry"), (8, -1, "wet"),
    (9, 1, "wet"), (9, -1, "dry"),
    (10, 1, "tight"), (10, -1, "loose"),
    (11, 1, "loose"), (11, -1, "tight"),
    (12, 1, "forward"), (12, -1, "pulled back"),
    (13, 1, "distant"), (13, -1, "close"),
    (14, 1, "smooth"), (14, -1, "rough"),
    (15, 1, "rough"), (15, -1, "smooth"),
]


class Vibe:
    """16-dimensional vibe descriptor. Each dim in [0, 1]."""

    __slots__ = ("dims",)

    def __init__(self, dims: Optional[List[float]] = None):
        if dims is None:
            self.dims = [0.5] * 16
        else:
            if len(dims) != 16:
                raise ValueError(f"Expected 16 dims, got {len(dims)}")
            self.dims = [max(0.0, min(1.0, float(d))) for d in dims]

    def __getitem__(self, idx: int) -> float:
        return self.dims[idx]

    def __setitem__(self, idx: int, val: float):
        self.dims[idx] = max(0.0, min(1.0, float(val)))

    def __repr__(self) -> str:
        return f"Vibe({self.dims})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vibe):
            return NotImplemented
        return self.dims == other.dims

    def copy(self) -> "Vibe":
        return Vibe(self.dims[:])

    def blend(self, other: "Vibe", ratio: float = 0.5) -> "Vibe":
        """Linearly blend with another vibe. ratio=0 → self, ratio=1 → other."""
        r = max(0.0, min(1.0, ratio))
        return Vibe([s * (1 - r) + o * r for s, o in zip(self.dims, other.dims)])

    def distance(self, other: "Vibe") -> float:
        """Euclidean distance between two vibes."""
        return math.sqrt(sum((s - o) ** 2 for s, o in zip(self.dims, other.dims)))

    def diffuse(self, neighbors: List["Vibe"], weights: Optional[List[float]] = None,
                coeff: float = 0.1) -> "Vibe":
        """Diffuse toward weighted average of neighbors."""
        if not neighbors:
            return self.copy()
        if weights is None:
            weights = [1.0 / len(neighbors)] * len(neighbors)
        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]
        avg = [0.0] * 16
        for w, n in zip(weights, neighbors):
            for i in range(16):
                avg[i] += w * n.dims[i]
        return Vibe([s * (1 - coeff) + a * coeff for s, a in zip(self.dims, avg)])

    def energy(self) -> float:
        """Total energy (L2 norm)."""
        return math.sqrt(sum(d * d for d in self.dims))

    def groove_lock(self, other: "Vibe") -> float:
        """Cosine similarity with another vibe. 1.0 = perfect lock."""
        dot = sum(s * o for s, o in zip(self.dims, other.dims))
        se = self.energy()
        oe = other.energy()
        if se == 0 or oe == 0:
            return 0.0
        return dot / (se * oe)

    def qualitative_description(self) -> str:
        """Human-readable description of dominant dims."""
        ranked = sorted(range(16), key=lambda i: -self.dims[i])
        top = ranked[:4]
        parts = []
        for idx in top:
            val = self.dims[idx]
            if val > 0.65:
                parts.append(DIM_NAMES[idx])
            elif val < 0.35:
                # Opposite
                opp = idx + 1 if idx % 2 == 0 else idx - 1
                parts.append(f"low-{DIM_NAMES[idx]}")
        if not parts:
            return "neutral"
        return ", ".join(parts)

    @staticmethod
    def from_description(text: str) -> "Vibe":
        """Create a Vibe delta from a text description."""
        dims = [0.5] * 16
        words = re.findall(r"[a-z]+", text.lower())
        for word in words:
            if word in _KEYWORD_MAP:
                idx, sign = _KEYWORD_MAP[word]
                dims[idx] = min(1.0, dims[idx] + 0.3 * sign)
        return Vibe(dims)
