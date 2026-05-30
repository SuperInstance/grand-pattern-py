"""Test suite for grand_pattern — 23 tests covering all modules."""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from grand_pattern import (
    Vibe, VectorDb, Jepa, Murmur, MurmurPacket, MurmurLevel, GossipRound,
    Tick, TickSchedule, Tempo, TMinusEvent,
    Signal, SignalType, Port, Route, RouteAlgorithm, Router,
    Room, CellGraph,
)

passed = 0
failed = 0


def test(name):
    def decorator(fn):
        def wrapper():
            global passed, failed
            try:
                fn()
                passed += 1
                print(f"  ✓ {name}")
            except Exception as e:
                failed += 1
                print(f"  ✗ {name}: {e}")
        wrapper._name = name
        return wrapper
    return decorator


# ─── Vibe tests (1-5) ───

@test("1: Vibe creation and indexing")
def t1():
    v = Vibe([0.1] * 16)
    assert v[0] == 0.1
    assert len(v.dims) == 16
    v2 = Vibe()  # default 0.5
    assert v2[0] == 0.5

@test("2: Vibe blend")
def t2():
    a = Vibe([0.0] * 16)
    b = Vibe([1.0] * 16)
    mid = a.blend(b, 0.5)
    assert all(abs(d - 0.5) < 1e-9 for d in mid.dims)

@test("3: Vibe distance")
def t3():
    a = Vibe([0.0] * 16)
    b = Vibe([1.0] * 16)
    d = a.distance(b)
    assert abs(d - math.sqrt(16)) < 1e-9

@test("4: Vibe diffuse")
def t4():
    center = Vibe([0.5] * 16)
    neighbors = [Vibe([1.0] * 16), Vibe([0.0] * 16)]
    diffused = center.diffuse(neighbors, coeff=0.2)
    assert all(abs(d - 0.5) < 1e-9 for d in diffused.dims)

@test("5: Vibe qualitative description")
def t5():
    v = Vibe([0.9, 0.1] + [0.5] * 14)  # very dark, low bright
    desc = v.qualitative_description()
    assert "dark" in desc


# ─── Jepa tests (6-10) ───

@test("6: Jepa perceive")
def t6():
    j = Jepa()
    j.perceive(Vibe([0.8] * 16))
    assert j.perception_db.size() == 1

@test("7: Jepa predict")
def t7():
    j = Jepa()
    j.perceive(Vibe([0.8] * 16))
    j.perceive(Vibe([0.8] * 16))
    pred = j.predict()
    assert abs(pred[0] - 0.8) < 1e-9

@test("8: Jepa surprise")
def t8():
    j = Jepa()
    j.perceive(Vibe([0.0] * 16))
    j.perceive(Vibe([0.0] * 16))
    # Observe something very different
    s = j.surprise(Vibe([1.0] * 16))
    assert s > 0.5

@test("9: Jepa conservation")
def t9():
    j = Jepa()
    for i in range(5):
        j.perceive(Vibe([0.6] * 16))
        j.record_prediction()
    c = j.check_conservation()
    assert c < 0.5  # predictions ≈ perceptions

@test("10: Jepa gc")
def t10():
    j = Jepa()
    for i in range(200):
        j.perceive(Vibe([i / 200.0] * 16))
    j.gc(max_entries=50)
    assert j.perception_db.size() == 50


# ─── Murmur tests (11-13) ───

@test("11: Murmur create and ingest")
def t11():
    m = Murmur("node-1")
    p = MurmurPacket("node-2", Vibe([0.7] * 16), MurmurLevel.NEIGHBOR, ttl=3)
    m.ingest(p)
    assert not m.is_empty()

@test("12: Murmur decay")
def t12():
    m = Murmur("node-1")
    p = MurmurPacket("node-2", Vibe([0.7] * 16), ttl=0)  # already TTL=0
    m.ingest(p)
    m.decay_all()
    assert m.is_empty()

@test("13: Gossip round")
def t13():
    m1 = Murmur("a")
    m2 = Murmur("b")
    m1.ingest(MurmurPacket("a", Vibe([0.5] * 16), ttl=5))
    gr = GossipRound()
    packets = gr.send(m1, max_packets=5)
    gr.receive(m2, packets)
    summary = gr.summary()
    assert summary["sent"] > 0
    assert summary["received"] > 0


# ─── Tick tests (14-15) ───

@test("14: Tick schedule")
def t14():
    ts = TickSchedule(tick_interval=0.01)
    t1 = ts.next_tick()
    t2 = ts.next_tick()
    assert t2.timestamp >= t1.timestamp

@test("15: Tempo adapt")
def t15():
    tempo = Tempo(bpm=120.0)
    tempo.adapt(1.0)  # max energy → speed up
    assert tempo.bpm > 120.0
    tempo2 = Tempo(bpm=120.0)
    tempo2.adapt(0.0)  # min energy → slow down
    assert tempo2.bpm < 120.0


# ─── Signal tests (16-17) ───

@test("16: Router direct")
def t16():
    r = Router()
    r.add_port("a:out", is_output=True)
    r.add_port("b:in")
    r.add_route("a:out", "b:in", RouteAlgorithm.DIRECT)
    sig = Signal("a:out", None, SignalType.VIBE, Vibe([0.5] * 16))
    delivered = r.send(sig)
    assert delivered == 1
    received = r.receive("b:in")
    assert len(received) == 1

@test("17: Router deadband (on_change)")
def t17():
    r = Router()
    r.add_port("a:out", is_output=True)
    r.add_port("b:in")
    r.add_route("a:out", "b:in", RouteAlgorithm.ON_CHANGE, deadband=0.5)
    v = Vibe([0.5] * 16)
    sig1 = Signal("a:out", None, SignalType.VIBE, v)
    assert r.send(sig1) == 1  # first always sends
    # Same value → dropped
    sig2 = Signal("a:out", None, SignalType.VIBE, v)
    assert r.send(sig2) == 0  # below deadband


# ─── CellGraph tests (18-23) ───

@test("18: CellGraph tick")
def t18():
    g = CellGraph()
    g.add_room("r1", Vibe([0.5] * 16))
    g.add_room("r2", Vibe([0.6] * 16))
    t = g.tick()
    assert t == 1

@test("19: CellGraph gossip")
def t19():
    g = CellGraph()
    g.add_room("r1", Vibe([0.5] * 16))
    g.add_room("r2", Vibe([0.6] * 16))
    g.add_edge("r1", "r2")
    result = g.gossip()
    assert result["sent"] > 0
    assert result["received"] > 0

@test("20: CellGraph chain topology")
def t20():
    g = CellGraph()
    g.add_room("a")
    g.add_room("b")
    g.add_room("c")
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    assert "c" in g.edges.get("b", set())
    assert "a" in g.edges.get("b", set())

@test("21: CellGraph mesh topology")
def t21():
    g = CellGraph()
    for i in range(4):
        g.add_room(f"r{i}")
    # Full mesh
    for i in range(4):
        for j in range(i + 1, 4):
            g.add_edge(f"r{i}", f"r{j}")
    assert len(g.edges["r0"]) == 3
    g.tick()
    g.gossip()
    assert g.fleet_vibe() is not None

@test("22: Fleet vibe average")
def t22():
    g = CellGraph()
    g.add_room("r1", Vibe([0.0] * 16))
    g.add_room("r2", Vibe([1.0] * 16))
    fv = g.fleet_vibe()
    assert abs(fv[0] - 0.5) < 1e-9

@test("23: Anomaly detection")
def t23():
    g = CellGraph()
    g.add_room("normal", Vibe([0.5] * 16))
    g.add_room("weird", Vibe([0.5] * 16))
    # Train on consistent data
    for _ in range(5):
        g.rooms["normal"].perceive(Vibe([0.5] * 16))
        g.rooms["weird"].perceive(Vibe([0.5] * 16))
    # Now weird room gets a very different vibe
    g.rooms["weird"].perceive(Vibe([0.0] * 16))
    g.rooms["weird"].vibe = Vibe([0.0] * 16)
    anomalies = g.detect_anomaly(threshold=0.1)
    assert "weird" in anomalies


# ─── Run ───

if __name__ == "__main__":
    print("Running grand_pattern tests...\n")
    # Collect all test functions sorted by name
    tests = [(name, obj) for name, obj in sorted(globals().items())
             if callable(obj) and hasattr(obj, '_name')]
    for name, t in tests:
        t()
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed:
        sys.exit(1)
    print("All tests passed! ✓")
