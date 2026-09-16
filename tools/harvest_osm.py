#!/usr/bin/env python3
"""harvest_osm.py — every place OpenStreetMap ties to donuts, in all fifty states.

One Overpass query per state (a single nationwide regex query times out), ways and
relations reduced to a centre point. Output is a harvest file, never a record:
data/harvest/osm-places.json, carrying the licence (ODbL 1.0, share-alike), the fetch
time and the query itself, so an absence reads as "not in OSM on that date" rather
than "does not exist".

Two matchers, and every row says which one caught it:
  cuisine  cuisine=donut / doughnut / donuts
  name     donut, doughnut or dønut in the name of a bakery, pastry shop, cafe,
           fast-food counter or restaurant

A name match is weaker and this file says so. Every row also carries `chain`: true when
OSM gives it a brand or brand:wikidata, so a reader can take the chains off the map.

    python3 tools/harvest_osm.py             # fetch every state and write
    python3 tools/harvest_osm.py --dry       # counts only, writes nothing
    python3 tools/harvest_osm.py --states NY,PA
    python3 tools/harvest_osm.py --towns     # reverse-geocode rows with no addr:city

Refuses to overwrite a previous harvest with a much smaller one (a zero-element
Overpass reply is valid and looks exactly like "no wings in America").
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HARVEST, jdump, jload, slugify, state_by_geo  # noqa: E402

UA = "pink-box-build/0.1 (https://wichaa.net; nan@motdang.net) python-urllib"
# Overpass mirrors, tried in turn. The main endpoint throttles hard on fifty queries in
# a row and starts refusing connections outright; rotating keeps a long harvest alive.
ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter",
             "https://overpass.osm.jp/api/interpreter",
             "https://overpass.private.coffee/api/interpreter"]
ENDPOINT = ENDPOINTS[0]
OUT = HARVEST / "osm-places.json"

STATES = ("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
          "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY").split()

# cuisine values OSM actually carries for this food, and the eateries a name match is allowed in
CUISINE_RE = "donut|doughnut|donuts|doughnuts"
NAME_RE = "[Dd]o[u]?n[u]?ghts?nut|[Dd]onut|[Dd]oughnut|DONUT|DOUGHNUT"
NOT_DONUTS = ()   # "donut" in a name is not ambiguous the way "wing" was
AMENITIES = "restaurant|fast_food|cafe"
SHOPS = "bakery|pastry|confectionery|convenience"

QUERY_TMPL = ('[out:json][timeout:180];'
              'area["ISO3166-2"="US-{st}"][admin_level]->.a;'
              '('
              'nwr["cuisine"~"{cu}",i](area.a);'
              'nwr["amenity"~"{am}"]["name"~"{nm}"](area.a);'
              'nwr["shop"~"{sh}"]["name"~"{nm}"](area.a);'
              'nwr["shop"~"{sh}"]["cuisine"~"{cu}",i](area.a);'
              ');'
              'out center tags;')

KEEP = ("name", "amenity", "shop", "cuisine", "addr:housenumber", "addr:street", "addr:city", "addr:state", "addr:postcode",
        "phone", "website", "opening_hours", "brand", "brand:wikidata", "wikidata", "wikipedia", "check_date",
        "takeaway", "delivery", "outdoor_seating", "wheelchair", "contact:facebook", "smoking", "start_date",
        "lgbtq", "lgbtq:signed", "diet:halal", "drive_through", "payment:cash", "payment:cards", "description")


def fetch(query: str, tries=8) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for i in range(tries):
        ep = ENDPOINTS[i % len(ENDPOINTS)]
        req = urllib.request.Request(ep, data=data, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            last = e
            wait = min(15 * (i + 1), 90)
            print(f"    {ep.split('/')[2]}: {e} — waiting {wait}s", flush=True)
            time.sleep(wait)
    raise last


def classify(tags: dict) -> str | None:
    """'cuisine' (OSM says donuts), 'name' (the name says donut), or None."""
    cu = (tags.get("cuisine") or "").lower()
    parts = [x.strip() for x in cu.replace(";", ",").split(",")]
    if any(p in ("donut", "donuts", "doughnut", "doughnuts") for p in parts):
        return "cuisine"
    n = (tags.get("name") or "").lower()
    if "donut" in n or "doughnut" in n or "do-nut" in n:
        return "name"
    return None


def state_of(tags: dict, lat: float, lon: float, fallback: str) -> str:
    s = (tags.get("addr:state") or "").strip().upper()
    if len(s) == 2 and s in STATES:
        return s
    return state_by_geo(lat, lon) or fallback


def main(dry=False, only: list[str] | None = None) -> int:
    t0 = time.time()
    want = only or STATES
    rows: list[dict] = []
    seen: set[str] = set()
    ids: set[str] = set()
    per_state: dict[str, int] = {}
    query_shown = ""
    for st in want:
        q = QUERY_TMPL.format(st=st, cu=CUISINE_RE, am=AMENITIES, sh=SHOPS, nm=NAME_RE)
        query_shown = query_shown or QUERY_TMPL.format(st="XX", cu=CUISINE_RE, am=AMENITIES, sh=SHOPS, nm=NAME_RE)
        try:
            raw = fetch(q)
        except Exception as e:  # noqa: BLE001
            print(f"  {st}: FAILED {e}", flush=True)
            continue
        got = 0
        for e in raw.get("elements", []):
            tags = e.get("tags", {})
            if not tags.get("name"):
                continue
            how = classify(tags)
            if not how:
                continue
            lat = e.get("lat") or (e.get("center") or {}).get("lat")
            lon = e.get("lon") or (e.get("center") or {}).get("lon")
            if lat is None or lon is None:
                continue
            osm_id = f"{e['type']}/{e['id']}"
            if osm_id in ids:
                continue
            ids.add(osm_id)
            state = state_of(tags, lat, lon, st)
            base = slugify(tags["name"]) or "unnamed"
            slug = base
            n = 2
            while slug in seen:
                city = slugify(tags.get("addr:city", "")) or f"{lat:.3f}{lon:.3f}".replace(".", "").replace("-", "")
                slug = f"{base}-{city}" if n == 2 and city else f"{base}-{n}"
                n += 1
            seen.add(slug)
            rows.append({
                "osm_id": osm_id, "slug": slug, "name": tags["name"], "state": state, "match": how,
                "chain": bool(tags.get("brand") or tags.get("brand:wikidata")),
                "lat": round(lat, 5), "lon": round(lon, 5),
                "tags": {k: v for k, v in tags.items() if k in KEEP},
            })
            got += 1
        per_state[st] = got
        print(f"  {st} {got:5d}   ({len(rows)} so far, {time.time()-t0:.0f}s)", flush=True)
        if not dry:
            _save(rows, per_state, query_shown, merge=True)   # a kill mid-harvest keeps the states already done
        time.sleep(2)
    rows.sort(key=lambda r: (r["state"], r["name"].lower()))
    by_cuisine = sum(1 for r in rows if r["match"] == "cuisine")
    print(f"{len(rows)} named places · {by_cuisine} by cuisine · {len(rows)-by_cuisine} by name · {time.time()-t0:.0f}s")
    if dry:
        return 0
    if OUT.exists() and only is None:
        prev = len(jload(OUT).get("places", []))
        if rows and len(rows) < prev * 0.75:
            print(f"refused: previous harvest had {prev} places, this one {len(rows)} (>25% shrink). Delete {OUT} to force.")
            return 3
    if not rows:
        print("refused: zero places is a valid Overpass reply and would be cached as absence")
        return 3
    _save(rows, per_state, query_shown, merge=True)
    print(f"wrote {OUT} — {len(jload(OUT)['places'])} rows in all")
    return 0


def _save(rows: list, per_state: dict, query_shown: str, merge=True) -> None:
    """Write the harvest, merging with whatever is already on disk. Called after every
    state, so an interrupted run keeps the states it finished."""
    keep: dict = {}
    if merge and OUT.exists():
        prev = jload(OUT)
        keep = {r["osm_id"]: r for r in prev["places"]}
        per_state = {**prev.get("by_state", {}), **per_state}
    for r in rows:
        keep[r["osm_id"]] = r
    out = sorted(keep.values(), key=lambda r: (r["state"], r["name"].lower()))
    jdump({
        "source": "OpenStreetMap contributors", "license": "ODbL 1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "endpoint": ENDPOINT, "query": query_shown,
        "matchers": {"cuisine": "cuisine=wings / chicken_wings / buffalo_wings",
                     "name": "the word 'wing' in the name of a restaurant, fast-food counter, bar, pub or cafe, "
                             "excluding rows tagged with a cuisine that means something else"},
        "count": len(out), "by_state": per_state, "places": out,
    }, OUT)


# ------------------------------------------------------------------ towns and counties
NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
TOWNS = HARVEST / "osm-towns.json"


def towns(sleep=1.1, limit=None) -> int:
    """OSM rows without addr:city cannot be grouped by town. Nominatim's reverse geocoder
    fills town and county from the same OSM data, one request per second as its usage
    policy asks, cached by osm_id so a re-run fetches only new rows."""
    if not OUT.exists():
        print("no harvest yet")
        return 1
    h = jload(OUT)
    cache = jload(TOWNS) if TOWNS.exists() else {"source": "Nominatim reverse geocoding of OpenStreetMap data, ODbL", "rows": {}}
    rows = cache["rows"]
    todo = [p for p in h["places"] if p["osm_id"] not in rows and not p["tags"].get("addr:city")]
    print(f"{len(todo)} rows need a town; {len(rows)} already cached")
    n = 0
    for p in todo[:limit] if limit else todo:
        q = urllib.parse.urlencode({"lat": p["lat"], "lon": p["lon"], "format": "jsonv2", "zoom": 10, "addressdetails": 1})
        req = urllib.request.Request(f"{NOMINATIM}?{q}", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"  {p['name']}: {e}")
            time.sleep(sleep)
            continue
        a = d.get("address", {})
        town = a.get("city") or a.get("town") or a.get("village") or a.get("hamlet") or a.get("municipality") or ""
        county = (a.get("county") or "").replace(" County", "")
        rows[p["osm_id"]] = {"town": town, "county": county, "state": a.get("state", ""), "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        n += 1
        if n % 50 == 0:
            jdump(cache, TOWNS)
            print(f"  {n} geocoded…", flush=True)
        time.sleep(sleep)
    jdump(cache, TOWNS)
    print(f"towns: {n} new, {len(rows)} cached → {TOWNS}")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--towns" in argv:
        lim = None
        if "--limit" in argv:
            lim = int(argv[argv.index("--limit") + 1])
        sys.exit(towns(limit=lim))
    picked = None
    if "--states" in argv:
        picked = [s.strip().upper() for s in argv[argv.index("--states") + 1].split(",") if s.strip()]
    if "--resume" in argv and OUT.exists():
        have = {r["state"] for r in jload(OUT)["places"]}
        picked = [s for s in (picked or STATES) if s not in have]
        print(f"resuming: {len(picked)} states still to fetch — {','.join(picked)}")
        if not picked:
            sys.exit(0)
    sys.exit(main(dry="--dry" in argv, only=picked))
