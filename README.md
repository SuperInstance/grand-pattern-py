# grand-pattern-py

Pure Python Grand Pattern toolkit — standalone cellular graph intelligence.

## Install

```bash
pip install grand-pattern
```

## Overview

Grand Pattern is a toolkit for **cellular graph intelligence** — interconnected cells (rooms) that perceive, predict, gossip, and route signals through a shared vibe space.

### Primitives

| Module | Description |
|--------|-------------|
| **Vibe** | 16-dimensional emotional/spectral descriptor with blend, diffuse, groove lock |
| **Jepa** | Perception/prediction/surprise engine with dual vector databases |
| **Murmur** | Gossip protocol for distributed vibe propagation with TTL & decay |
| **Tick** | Temporal scheduling with swing, adaptive tempo, countdown events |
| **Signal** | Routing with 6 algorithms (direct, buffered, correlated, on_change, sampled, adaptive), deadband, storm detection |
| **Room** | Composes Vibe + Jepa + Murmur into a single cell |
| **CellGraph** | Full cellular graph — rooms, edges, gossip rounds, fleet analytics |

### Quick Start

```python
from grand_pattern import CellGraph, Vibe

graph = CellGraph()
graph.add_room("living", Vibe([0.8, 0.3, 0.9] + [0.5]*13))  # dark, warm
graph.add_room("kitchen", Vibe([0.2, 0.9, 0.7] + [0.5]*13))  # bright, warm
graph.add_edge("living", "kitchen")

graph.tick()
graph.gossip()

print(graph.fleet_vibe().qualitative_description())
print(graph.summary())
```

## Development

```bash
python3 test_all.py
```

## License

MIT
