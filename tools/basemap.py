#!/usr/bin/env python3
"""basemap.py — the ground under the small maps: land, water, state lines, roads, towns.

Natural Earth 1:10m, public domain (naturalearthdata.com). The raw layers download once,
with curl, into a cache shared by every project on this machine (NE_CACHE, default
~/.cache/naturalearth). This script clips them to the boxes this site's maps draw and
writes data/geo/basemap.json; the build reads only that file, and the page carries the
result as inline SVG.

    python3 tools/basemap.py            # re-clip after adding places
    fr = Frame(lat, lon, w=760, h=470, km=250)     # equal metres on both axes
    svg = draw(fr, load(), avoid=[(x, y, r)])      # <g> of land, water, lines, towns
    # the <svg> that holds them carries class="bm", and the page carries CSS
    bar = scale_bar(fr)                            # a round number of miles, measured

The projection is equirectangular about the frame's centre, x scaled by cos(latitude),
so a kilometre east is as long on the page as a kilometre north at the centre line.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "geo" / "basemap.json"
CACHE = Path(os.environ.get("NE_CACHE") or (Path.home() / ".cache" / "naturalearth"))
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
CREDIT = "Natural Earth 1:10m — land, coastline, lakes, rivers, roads, admin-0 and admin-1 lines, populated places (public domain)"
SITE = "https://www.naturalearthdata.com/"
COUNTRIES = {"USA", "CAN", "MEX"}
TOL = 0.002          # degrees, Douglas-Peucker at clip time; ~200 m
KM_MI = 1.609344
R_KM = 6371.0088

E = __import__("html").escape

CSS = (
    ".bm{--bm-sea:#d4e3ea;--bm-land:#f7f2e9;--bm-road:#d5c4aa;--bm-road2:#e3d7c4;--bm-adm:#8c7f6e;"
    "--bm-river:#9fbfcc;--bm-town:#5f564b;--bm-halo:#f7f2e9;--bm-pin:#8a8176}"
    "@media (prefers-color-scheme:dark){:root:not([data-theme=\"light\"]) .bm{--bm-sea:#15232a;--bm-land:#221e1a;"
    "--bm-road:#5b4e3f;--bm-road2:#40372d;--bm-adm:#8f8575;--bm-river:#2f5664;--bm-town:#c4b9a8;--bm-halo:#221e1a;--bm-pin:#a39a8c}}"
    ":root[data-theme=\"dark\"] .bm{--bm-sea:#15232a;--bm-land:#221e1a;--bm-road:#5b4e3f;--bm-road2:#40372d;"
    "--bm-adm:#8f8575;--bm-river:#2f5664;--bm-town:#c4b9a8;--bm-halo:#221e1a;--bm-pin:#a39a8c}"
    ".bm text{font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,sans-serif;font-weight:600;"
    "paint-order:stroke;stroke:var(--bm-halo);stroke-width:3.5px;stroke-linejoin:round}"
    ".bm .tn{font-size:15px;fill:var(--bm-town)}.bm .t2{font-size:13px;font-weight:500}"
    ".bm .sb{font-size:14px;fill:var(--bm-town)}"
    "@media (max-width:560px){.bm .tn{font-size:26px;stroke-width:6px}.bm .t2,.bm .d2{display:none}"
    ".bm .sb{font-size:24px;stroke-width:6px}}"
)


# ------------------------------------------------------------------ geometry

class Frame:
    """A w×h pixel window centred on (lat, lon), k kilometres to the pixel."""

    def __init__(self, lat: float, lon: float, w: int = 760, h: int = 470, km: float = 250.0):
        self.lat, self.lon, self.w, self.h = lat, lon, w, h
        self.k = km / w
        self.c = math.cos(math.radians(lat))
        dlon = math.degrees(km / 2 / (R_KM * self.c))
        dlat = math.degrees(self.k * h / 2 / R_KM)
        self.box = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)

    @classmethod
    def fit(cls, pts: list, w: int, h: int, pad: float = 0.12, min_km: float = 120.0) -> "Frame":
        """The smallest frame that holds every (lat, lon) with pad on each side. The short
        side widens to keep the shape; it is never stretched."""
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        lat0 = (min(lats) + max(lats)) / 2
        lon0 = (min(lons) + max(lons)) / 2
        c = math.cos(math.radians(lat0))
        wkm = math.radians(max(lons) - min(lons)) * R_KM * c
        hkm = math.radians(max(lats) - min(lats)) * R_KM
        km = max(wkm, hkm * w / h, min_km) * (1 + 2 * pad)
        return cls(lat0, lon0, w, h, km)

    def xy(self, lon: float, lat: float) -> tuple:
        x = self.w / 2 + math.radians(lon - self.lon) * R_KM * self.c / self.k
        y = self.h / 2 - math.radians(lat - self.lat) * R_KM / self.k
        return x, y

    def inside(self, lon: float, lat: float, margin: float = 0.0) -> bool:
        x, y = self.xy(lon, lat)
        return margin <= x <= self.w - margin and margin <= y <= self.h - margin


def _perp(p, a, b) -> float:
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def simplify(pts: list, tol: float) -> list:
    """Douglas-Peucker, iterative so a long coastline does not blow the stack."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        far, d = -1, tol
        for k in range(i + 1, j):
            dk = _perp(pts[k], pts[i], pts[j])
            if dk > d:
                far, d = k, dk
        if far > 0:
            keep[far] = True
            stack.append((i, far))
            stack.append((far, j))
    return [p for p, k in zip(pts, keep) if k]


def clip_ring(ring: list, box: tuple) -> list:
    """Sutherland-Hodgman against a rectangle. A concave ring comes back with seams along
    the edge, which a fill without a stroke does not show."""
    x0, y0, x1, y1 = box
    edges = (
        (lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
        (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1)),
    )
    out = list(ring)
    for ins, cut in edges:
        if not out:
            break
        src, out = out, []
        prev = src[-1]
        for cur in src:
            if ins(cur):
                if not ins(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif ins(prev):
                out.append(cut(prev, cur))
            prev = cur
    return out


def clip_line(line: list, box: tuple) -> list:
    """Liang-Barsky per segment; returns the pieces of the line inside the box."""
    x0, y0, x1, y1 = box
    pieces, cur = [], []
    for a, b in zip(line, line[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t0, t1, ok = 0.0, 1.0, True
        for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
            if p == 0:
                if q < 0:
                    ok = False
                    break
                continue
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                ok = False
                break
        if not ok:
            if cur:
                pieces.append(cur)
                cur = []
            continue
        pa = (a[0] + t0 * dx, a[1] + t0 * dy)
        pb = (a[0] + t1 * dx, a[1] + t1 * dy)
        if not cur:
            cur = [pa]
        elif cur[-1] != pa:
            pieces.append(cur)
            cur = [pa]
        cur.append(pb)
        if t1 < 1.0:
            pieces.append(cur)
            cur = []
    if cur:
        pieces.append(cur)
    return [p for p in pieces if len(p) >= 2]


def _bbox(pts) -> tuple:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _meets(a: tuple, b: tuple) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def _within(a: tuple, b: tuple) -> bool:
    return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]


# ------------------------------------------------------------------ preparing the data

LAYERS = {
    "land": "ne_10m_land",
    "coast": "ne_10m_coastline",
    "lakes": "ne_10m_lakes",
    "lakes_na": "ne_10m_lakes_north_america",
    "rivers": "ne_10m_rivers_lake_centerlines",
    "rivers_na": "ne_10m_rivers_north_america",
    "adm0": "ne_10m_admin_0_boundary_lines_land",
    "adm1": "ne_10m_admin_1_states_provinces_lines",
    "adm1_poly": "ne_10m_admin_1_states_provinces",
    "roads": "ne_10m_roads",
    "towns": "ne_10m_populated_places_simple",
}


def _layer(name: str) -> list:
    f = CACHE / (LAYERS[name] + ".geojson")
    if not f.exists() or f.stat().st_size == 0:
        CACHE.mkdir(parents=True, exist_ok=True)
        print(f"fetching {f.name}")
        subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(f), NE + f.name], check=True)
    with open(f, encoding="utf-8") as fh:
        return json.load(fh)["features"]


def _parts(geom: dict) -> list:
    if not geom:
        return []
    t, c = geom["type"], geom["coordinates"]
    if t in ("LineString",):
        return [c]
    if t in ("MultiLineString", "Polygon"):
        return list(c)
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


def merge_boxes(boxes: list, pad: float = 0.3) -> list:
    """Overlapping boxes join, so a frame always lies inside one prepared box."""
    out = [(b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad) for b in boxes]
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                if _meets(out[i], out[j]):
                    a, b = out[i], out[j]
                    out[i] = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
                    del out[j]
                    changed = True
                    break
            if changed:
                break
    return [tuple(round(v, 3) for v in b) for b in out]


def _rnd(pts) -> list:
    return [[round(x, 4), round(y, 4)] for x, y in pts]


def prepare(boxes: list, out: Path = OUT) -> dict:
    boxes = merge_boxes(boxes)
    data = {"source": CREDIT, "url": SITE, "coords": "[lon, lat], 4 dp, Douglas-Peucker at %s°" % TOL,
            "boxes": boxes, "land": [], "coast": [], "lakes": [], "rivers": [], "adm0": [], "adm1": [],
            "roads": [], "towns": [], "states": {}}

    def rings(layer, key, keep=lambda p: True):
        for f in _layer(layer):
            if not keep(f["properties"]):
                continue
            for ring in _parts(f["geometry"]):
                bb = _bbox(ring)
                for box in boxes:
                    if _meets(bb, box):
                        c = clip_ring([tuple(p[:2]) for p in ring], box)
                        c = simplify(c, TOL) if len(c) > 3 else c
                        if len(c) >= 3:
                            data[key].append(_rnd(c))

    def lines(layer, key, keep=lambda p: True, tag=lambda p: None):
        for f in _layer(layer):
            p = f["properties"]
            if not keep(p):
                continue
            for line in _parts(f["geometry"]):
                bb = _bbox(line)
                for box in boxes:
                    if _meets(bb, box):
                        for piece in clip_line([tuple(q[:2]) for q in line], box):
                            s = simplify(piece, TOL)
                            if len(s) >= 2:
                                t = tag(p)
                                data[key].append({"r": t, "c": _rnd(s)} if t is not None else _rnd(s))

    rings("land", "land")
    rings("lakes", "lakes")
    rings("lakes_na", "lakes")
    lines("coast", "coast")
    lines("rivers", "rivers", keep=lambda p: p.get("featurecla") != "Lake Centerline",
          tag=lambda p: int(p.get("scalerank") or 12))
    lines("rivers_na", "rivers", tag=lambda p: int(p.get("scalerank") or 12))
    lines("adm0", "adm0")
    lines("adm1", "adm1", keep=lambda p: p.get("ADM0_A3") in COUNTRIES)
    lines("roads", "roads",
          keep=lambda p: p.get("sov_a3") in COUNTRIES and p.get("featurecla") == "Road" and p.get("type") != "Ferry Route",
          tag=lambda p: int(p.get("scalerank") or 10) + (0 if p.get("type") in ("Major Highway", "Beltway") else 20))
    for f in _layer("towns"):
        p = f["properties"]
        if p.get("adm0_a3") not in COUNTRIES:
            continue
        lon, lat = p["longitude"], p["latitude"]
        if any(b[0] <= lon <= b[2] and b[1] <= lat <= b[3] for b in boxes):
            data["towns"].append({"n": p.get("nameascii") or p["name"], "lat": round(lat, 4), "lon": round(lon, 4),
                                  "pop": int(p.get("pop_max") or 0), "r": int(p.get("scalerank") or 10)})
    data["towns"].sort(key=lambda t: -t["pop"])
    # every US state's own box, for the coordinate gate
    for f in _layer("adm1_poly"):
        p = f["properties"]
        iso = p.get("iso_3166_2") or ""
        if p.get("iso_a2") == "US" and iso.startswith("US-"):
            pts = [q for ring in _parts(f["geometry"]) for q in ring]
            if pts:
                data["states"][iso[3:]] = [round(v, 3) for v in _bbox(pts)]
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, separators=(",", ":"))
        fh.write("\n")
    n = sum(len(data[k]) for k in ("land", "coast", "lakes", "rivers", "adm0", "adm1", "roads"))
    print(f"wrote {out.name}: {len(boxes)} boxes, {n} shapes, {len(data['towns'])} towns, "
          f"{out.stat().st_size / 1024:.0f} KB")
    return data


_LOADED: dict = {}


def load(path: Path = OUT) -> dict:
    if str(path) not in _LOADED:
        with open(path, encoding="utf-8") as fh:
            _LOADED[str(path)] = json.load(fh)
    return _LOADED[str(path)]


# ------------------------------------------------------------------ drawing

def _path(pts: list, closed: bool = False) -> str:
    s = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    return s + ("Z" if closed else "")


def _proj(fr: Frame, pts: list, tol: float) -> list:
    return simplify([fr.xy(lon, lat) for lon, lat in pts], tol)


def draw(fr: Frame, bm: dict, avoid: list = (), towns: int = 7) -> str:
    """Everything under the pins, clipped to the frame. avoid: (x, y, radius) circles a
    town label keeps clear of."""
    tol = 0.6
    box = fr.box
    pad = (box[0] - 0.05, box[1] - 0.05, box[2] + 0.05, box[3] + 0.05)

    def poly(key):
        d = []
        for ring in bm[key]:
            if not _meets(_bbox(ring), pad):
                continue
            c = clip_ring([tuple(p) for p in ring], pad)
            if len(c) >= 3:
                pp = _proj(fr, c, tol)
                if len(pp) >= 3:
                    d.append(_path(pp, True))
        return "".join(d)

    def line(items, keep=lambda r: True):
        d = []
        for it in items:
            pts, r = (it["c"], it["r"]) if isinstance(it, dict) else (it, None)
            if not keep(r) or not _meets(_bbox(pts), pad):
                continue
            for piece in clip_line([tuple(p) for p in pts], pad):
                pp = _proj(fr, piece, tol)
                if len(pp) >= 2 and (len(pp) > 2 or math.dist(pp[0], pp[-1]) > 1.5):
                    d.append(_path(pp))
        return "".join(d)

    k = fr.k                            # km per pixel: small = zoomed in
    road_cut = 8 if k < 0.6 else (6 if k < 1.5 else 4)
    minor_cut = 28 if k < 0.6 else (26 if k < 1.0 else -1)
    river_cut = 9 if k < 0.6 else (7 if k < 1.5 else 5)
    out = [f'<g><rect width="{fr.w}" height="{fr.h}" fill="var(--bm-sea)"/>']
    land = poly("land")
    if land:
        out.append(f'<path d="{land}" fill="var(--bm-land)" fill-rule="evenodd"/>')
    lakes = poly("lakes")
    if lakes:
        out.append(f'<path d="{lakes}" fill="var(--bm-sea)"/>')
    rv = line(bm["rivers"], lambda r: r is not None and r <= river_cut)
    if rv:
        out.append(f'<path d="{rv}" fill="none" stroke="var(--bm-river)" stroke-width="1.2" stroke-linejoin="round"/>')
    coast = line(bm["coast"])
    if coast:
        out.append(f'<path d="{coast}" fill="none" stroke="var(--bm-river)" stroke-width="1"/>')
    minor = line(bm["roads"], lambda r: 20 <= r <= minor_cut)
    if minor:
        out.append(f'<path class="d2" d="{minor}" fill="none" stroke="var(--bm-road2)" stroke-width="1.3" stroke-linejoin="round"/>')
    major = line(bm["roads"], lambda r: r <= road_cut)
    if major:
        out.append(f'<path d="{major}" fill="none" stroke="var(--bm-road)" stroke-width="2.2" stroke-linejoin="round"/>')
    a1 = line(bm["adm1"])
    if a1:
        out.append(f'<path d="{a1}" fill="none" stroke="var(--bm-adm)" stroke-width="1.3" stroke-dasharray="7 4"/>')
    a0 = line(bm["adm0"])
    if a0:
        out.append(f'<path d="{a0}" fill="none" stroke="var(--bm-adm)" stroke-width="2"/>')
    out.append(_towns(fr, bm, list(avoid), towns))
    out.append("</g>")
    return "".join(out)


def _towns(fr: Frame, bm: dict, avoid: list, n: int) -> str:
    """The biggest towns in the frame, labelled where the label fits. The first three are
    the ones a phone keeps."""
    placed = [(x - r, y - r, x + r, y + r) for x, y, r in avoid]
    out, got = [], 0
    for t in bm["towns"]:
        if got >= n:
            break
        if not fr.inside(t["lon"], t["lat"], 12):
            continue
        x, y = fr.xy(t["lon"], t["lat"])
        big = got < 3
        cw = 8.6 if big else 7.4          # desktop glyph width
        size = 15 if big else 13
        mw, ms = (15.0, 26) if big else (0, 0)   # the phone size, in the same units
        wd = max(len(t["n"]) * cw, len(t["n"]) * mw)
        hh = max(size, ms)
        ok = None
        for dx, anchor in ((7, "start"), (-7, "end")):
            x0 = x + dx if anchor == "start" else x + dx - wd
            bb = (x0, y - hh * 0.75, x0 + wd, y + hh * 0.35)
            if bb[0] < 4 or bb[2] > fr.w - 4 or bb[1] < 4 or bb[3] > fr.h - 30:
                continue
            if any(_meets(bb, p) for p in placed):
                continue
            ok = (dx, anchor, bb)
            break
        if not ok:
            continue
        dx, anchor, bb = ok
        placed.append(bb)
        placed.append((x - 4, y - 4, x + 4, y + 4))
        cls = "tn" if big else "tn t2"
        dot = "" if big else ' class="d2"'
        out.append(f'<circle{dot} cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="var(--bm-town)"/>'
                   f'<text class="{cls}" x="{x + dx:.1f}" y="{y + 5:.1f}" text-anchor="{anchor}">{E(t["n"])}</text>')
        got += 1
    return "".join(out)


def scale_bar(fr: Frame, x: float = 14, y: float = None) -> str:
    """A bar a round number of miles long, measured through the frame's own projection."""
    y = fr.h - 14 if y is None else y
    target = fr.w * fr.k / 5 / KM_MI
    mi = min((1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000), key=lambda v: abs(math.log(v / target)))
    px = mi * KM_MI / fr.k
    return (f'<g><path d="M{x:.1f} {y - 6:.1f}V{y:.1f}H{x + px:.1f}V{y - 6:.1f}" fill="none" '
            f'stroke="var(--bm-town)" stroke-width="2"/>'
            f'<text class="sb" x="{x + px + 8:.1f}" y="{y + 1:.1f}">{mi} mi</text></g>')


def pin_svg(x: float, y: float, colour: str, name: str = "", big: bool = False) -> str:
    if big:
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="16" fill="{colour}" opacity=".22"/>'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{colour}" stroke="var(--bm-halo)" stroke-width="2.5"/>')
    t = f"<title>{E(name)}</title>" if name else ""
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="var(--bm-pin)" stroke="var(--bm-halo)" '
            f'stroke-width="1.5">{t}</circle>')


# ------------------------------------------------------------------ the gate

def gate(points: list, frames: list, bm: dict = None) -> list:
    """points: (id, lat, lon, state) — the coordinate each place is drawn at.
    frames: (id, Frame, [(lat, lon), ...]) — every map and the pins it draws.
    Returns error strings, and prints what it checked."""
    bm = bm or load()
    states = bm.get("states", {})
    errs = []
    m = 0.05
    for pid, lat, lon, st in points:
        if lat is None or lon is None:
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            errs.append(f"{pid}: {lat}, {lon} is not a coordinate")
            continue
        b = states.get(st)
        if not b:
            errs.append(f"{pid}: state {st!r} has no box in basemap.json")
            continue
        inside = b[0] - m <= lon <= b[2] + m and b[1] - m <= lat <= b[3] + m
        swapped = b[0] - m <= lat <= b[2] + m and b[1] - m <= lon <= b[3] + m
        if not inside:
            errs.append(f"{pid}: {lat}, {lon} " + ("looks like lon/lat swapped" if swapped else f"is outside {st}")
                        + f" (lat {b[1]:.1f}..{b[3]:.1f}, lon {b[0]:.1f}..{b[2]:.1f})")
    pins = 0
    for fid, fr, pts in frames:
        if not any(_within(fr.box, bx) for bx in bm["boxes"]):
            errs.append(f"{fid}: map frame {tuple(round(v, 2) for v in fr.box)} is outside the prepared "
                        "basemap — run python3 tools/basemap.py")
        for lat, lon in pts:
            pins += 1
            if not fr.inside(lon, lat):
                x, y = fr.xy(lon, lat)
                errs.append(f"{fid}: pin {lat}, {lon} lands at {x:.0f},{y:.0f}, outside its {fr.w}×{fr.h} frame")
    print(f"map gate: {len(points)} coordinates against their state boxes and for lat/lon swaps, "
          f"{len(frames)} map frames against the prepared basemap, {pins} pins inside their frames — "
          f"{len(errs)} errors")
    return errs


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    import viz  # noqa: E402
    prepare(viz.basemap_boxes())
