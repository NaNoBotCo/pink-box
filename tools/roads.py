#!/usr/bin/env python3
"""roads.py — driving distance between places, from OSRM on OpenStreetMap data.

The build reads only data/geo/roads.json. This script fills it: one OSRM table request
per batch of up to 90 points, through curl (the system Python's LibreSSL cannot shake
hands with the server), a second apart.

    python3 tools/roads.py          # fetch what the cache lacks; a failed fetch warns, exits 0
    road_mi(a, b)                   # miles by road from the cache, or None

road_mi gives None when OSRM found no route, when a point snapped to a road more than
SNAP_M metres away (an island, a ferry, a coordinate in a field), or when the road is
shorter than the straight line or five times longer.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "data" / "geo" / "roads.json"
OSRM = "https://routing.openstreetmap.de/routed-car/table/v1/driving/"
CREDIT = "Road miles: OSRM on OpenStreetMap data (ODbL), routing.openstreetmap.de"
SNAP_M = 2000
BATCH = 90
KM_MI = 1.609344

_DATA: dict = {}


def key(lat: float, lon: float) -> str:
    return f"{lat:.4f},{lon:.4f}"


def _load() -> dict:
    if not _DATA:
        _DATA.update({"source": CREDIT, "snap_m": {}, "m": {}})
        if CACHE.exists():
            _DATA.update(json.loads(CACHE.read_text(encoding="utf-8")))
    return _DATA


def road_mi(a: tuple, b: tuple):
    """Miles by road from a=(lat, lon) to b, or None when the cache has no usable route."""
    d = _load()
    ka, kb = key(*a), key(*b)
    if ka == kb:
        return 0.0
    for k in (ka, kb):
        if d["snap_m"].get(k) is None or d["snap_m"][k] > SNAP_M:
            return None
    m = d["m"].get(ka + ">" + kb)
    if m is None:
        return None
    mi, crow = m / 1000 / KM_MI, crow_mi(a, b)
    # a road shorter than the straight line, or five times longer, is a routing fault
    return mi if crow * 0.98 <= mi <= max(crow * 5, crow + 5) else None


def crow_mi(a: tuple, b: tuple) -> float:
    """Great-circle miles between two (lat, lon) points."""
    p = math.radians
    h = (math.sin(p(b[0] - a[0]) / 2) ** 2
         + math.cos(p(a[0])) * math.cos(p(b[0])) * math.sin(p(b[1] - a[1]) / 2) ** 2)
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def _table(pts: list) -> dict:
    coords = ";".join(f"{lon:.5f},{lat:.5f}" for lat, lon in pts)
    r = subprocess.run(["curl", "-sS", "-m", "90", "-A", "nanobotco-sites/1 (map distances)",
                        OSRM + coords + "?annotations=distance"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or f"curl exit {r.returncode}")
    j = json.loads(r.stdout)
    if j.get("code") != "Ok":
        raise RuntimeError(j.get("message") or j.get("code"))
    return j


def fill(pts: list) -> int:
    """Fetch every pair among pts the cache lacks. Returns the number of requests made."""
    d = _load()
    pts = sorted({(round(a, 4), round(b, 4)) for a, b in pts})
    half = BATCH // 2
    chunks = [pts[i:i + half] for i in range(0, len(pts), half)]
    reqs = 0
    for i, ca in enumerate(chunks):
        for cb in chunks[i:]:
            batch = ca if cb is ca else ca + cb
            if all(key(*p) + ">" + key(*q) in d["m"] for p in batch for q in batch if p != q):
                continue
            if reqs:
                time.sleep(1.0)
            t = _table(batch)
            reqs += 1
            for p, w in zip(batch, t["sources"]):
                d["snap_m"][key(*p)] = round(w.get("distance", 0))
            for a, row in zip(batch, t["distances"]):
                for b, m in zip(batch, row):
                    if a != b:
                        d["m"][key(*a) + ">" + key(*b)] = None if m is None else round(m)
    if reqs:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(d, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    return reqs


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    import viz  # noqa: E402
    pts = viz.road_points()
    try:
        n = fill(pts)
        print(f"roads: {len(set(pts))} points, {n} OSRM requests, {len(_load()['m'])} pairs cached")
    except (RuntimeError, ValueError, OSError) as e:
        print(f"warn  roads: OSRM fetch failed ({e}); pages print straight-line miles where the cache has no road")
