#!/usr/bin/env python3
"""fetch_wiki.py — the verification corpus a drafting agent reads before it writes.

Plain-text copies of the Wikipedia articles this set cites, one file per article, each
carrying its title, URL and fetch date at the top. An agent reads these first and reaches
for the live web only when a fact is not in them.

    python3 tools/fetch_wiki.py <out-dir>

MediaWiki caps a full-text extract at one article per request, so this walks them one at
a time with a pause. Sixty-odd articles take about a minute.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "pink-box-build/0.1 (https://wichaa.net; nan@motdang.net) python-urllib"}

TITLES = """Doughnut|Doughnut hole|Cider doughnut|Cruller|Beignet|Malasada|Pączki|Fastnacht (doughnut)|
Berliner (doughnut)|Sufganiyah|Loukoumades|Zeppole|Churro|Mochi donut|Bear claw (pastry)|Apple fritter|
Long John (doughnut)|Boston cream doughnut|Maple bar|Kolach (pastry)|Klobásník|Funnel cake|Olykoek|
Krispy Kreme|Dunkin'|Tim Hortons|Shipley Do-Nuts|Randy's Donuts|Voodoo Doughnut|Top Pot Doughnuts|
Doughnut Plant|Winchell's Donut House|Mister Donut|Yum Yum Donuts|Daylight Donuts|LaMar's Donuts|
Duck Donuts|Federal Donuts|Donut King|Ted Ngoy|The Donut King (film)|Cambodian Americans|
Cambodian Americans in Long Beach, California|Long Beach, California|Stockton, California|Lowell, Massachusetts|
Khmer Rouge|Refugee Act of 1980|Hanson Gregory|Salvation Army|National Doughnut Day|Doughnut Lassie|
Adolph Levitt|Krispy Kreme Challenge|Café du Monde|Leonard's Bakery|Hamtramck, Michigan|Paczki Day|
Yeast|Baker's yeast|Proofing (baking technique)|Baking powder|Sodium bicarbonate|Shortening|Lard|
Deep frying|Frying|Canola oil|Trans fat|Buttermilk|Sour cream|Cake|Batter (cooking)|Dough|Wheat flour|
Powdered sugar|Glaze (cooking technique)|Sprinkles|Maple syrup|Custard|Bavarian cream|Fruit preserves|
Bacon, egg and cheese sandwich|Bodega (store)|Breakfast burrito|Egg roll|Lumpia|Cha gio|Fried rice|
Bubble tea|Tamale|Biscuits and gravy|Kolache Festival|Czech Americans|Vietnamese Americans|
Mississippi Delta Chinese|Greek Americans|Coffeehouse|Diner|Anthora|Drive-through|Strip mall|
American cuisine|Breakfast in the United States|Doughnut Corporation of America|Entenmann's|
Hostess Brands|Little Debbie|Dunkin' Donuts|Honey Dew Donuts|Allie's Donuts|Round Rock Donuts|
Britt's Donut Shop|Peter Pan Donut & Pastry Shop|The Doughnut Vault|Sublime Doughnuts|Bob's Donut & Pastry Shop|
Stan's Donuts|The Donut Hole|Hurts Donut Company|Psycho Donuts|Donut Friend|Voodoo Doughnut Too|
Mochinut|Holey Moley Coffee + Doughnuts|Donuts (film)|Sugar|Sucrose|Corn syrup|Vegetable oil|
Palm oil|FoodData Central|Nutrition facts label|Bakery|Pastry|Wheat|Gluten|Fermentation in food processing"""


def main(out_dir: str) -> int:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    titles = [t.strip() for t in TITLES.replace("\n", "").split("|") if t.strip()]
    got, missing = [], []
    for t in titles:
        q = {"action": "query", "prop": "extracts|info", "explaintext": 1, "format": "json",
             "redirects": 1, "inprop": "url", "titles": t}
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers=UA)
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:  # noqa: BLE001
            missing.append(f"{t} ({e})")
            continue
        for pid, pg in d["query"]["pages"].items():
            if int(pid) < 0 or not pg.get("extract"):
                missing.append(pg.get("title") or t)
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", pg["title"].lower()).strip("-")
            (out / f"{slug}.txt").write_text(
                f"TITLE: {pg['title']}\nURL: {pg['fullurl']}\nFETCHED: {time.strftime('%Y-%m-%d')}\n\n{pg['extract']}\n",
                encoding="utf-8")
            got.append(pg["title"])
        time.sleep(0.35)
    print(f"{len(got)} fetched into {out} · {len(missing)} missing: {missing}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(main(sys.argv[1]))
