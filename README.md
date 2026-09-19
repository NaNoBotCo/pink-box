# Pink Box

**cake or raised, egg rolls in the case, and who's been up since two** — a directory of
the American mom-and-pop donut shop, built the way [wichaa.net](https://wichaa.net) is
built: one JSON record per node of the trade, every field carrying where it came from,
every page saying what its neighbours are to it.

131 records · 476 kin links · 17 shops written up · 10,687 more off OpenStreetMap ·
9 donuts weighed by USDA · 30 pictures · 146 sources

## The two things it is about

**Cake or raised.** What lifts the donut decides everything downstream: how long it sits
in the fat (about 150 seconds against about 90), what it weighs (38 g against 24–28), how
much oil it carries, how it is finished, and how long it is worth selling. The published
accounts disagree about the oil, so [the site prints both](https://github.com/).

**The other menu.** Egg rolls, breakfast burritos, deli and bodega sandwiches, kolaches,
croissant sandwiches, fried rice, boba. Not a quirk — rent. Jolly Chan, who opened China
Express and Donut in San Francisco in 1993, told KQED the combination "came out of
necessity": "We have to sell more stuff to make up the rent and the expense."

## What is in it

| | |
|---|---|
| **Styles** | 15 — the Southern California pink box, the Texas kolache counter, the Southwest burrito counter, the New York corner counter, the orchard window, the hot light, Fastnacht Day, the Polish bakery counter, the malasada counter, the beignet stand, the Delta grocery counter, the mix-and-sign shop, the all-night counter, the novelty shop, Dunkin' country |
| **Donuts** | 21, grouped by dough: raised, cake, choux, potato, other — with eight carrying USDA's own measurements |
| **The rest of the case** | 10 — egg rolls, breakfast burritos, bacon egg and cheese, kolaches, klobasniky, fried rice, boba, tamales, biscuits and gravy, the pot of coffee |
| **Out back** | 12 — the raise, the proof box, the batter and depositor, the bench, the kettle, the fat, the glaze table, the filler, the night shift, day-old, the case |
| **Shops** | 17 written up, plus 10,687 rows off OpenStreetMap with chains marked |
| **People** | 8 — Ted Ngoy, Ning Yen, the Gregorys, Adolph Levitt, Bill Rosenberg, Vernon Rudolph, Russell Wendell |
| **Words** | 13 with their roots: donut against doughnut, olykoek, the hole, fry cake, bar, cruller, jimmies, dunking, day-old |
| **Stories** | cake against raised · the Donut King · why the egg rolls · the other menu, region by region · what counts as a mom-and-pop · bar or Long John · the sign outlives the owner · the franchise that vanished · the price of a dozen · where the shops actually are · where all of this came from |

## Pages that answer a question

- **/near/** — donut shops near you, sorted by distance, with filter chips for
  independents only, more than donuts, open today, and every ownership and counter tag.
  Each tag carries the source it came from.
- **/dough/** — cake against raised, drawn in cross-section and sitting in the fat.
- **/donut/** — the nine doughnut foods USDA has weighed: sugar and fat in one piece,
  grouped by dough, plus the span of what USDA itself calls a piece (13 g to 157 g).
- **/counter/** — who sells what besides donuts, one map panel per item, with the evidence.
- **/make/** — a glaze, a dough or a filling, every proportion naming its source.
- **/numbers/** — how far you are from the nearest counter anywhere in the lower 48.
- **/quiz/** — which donut shop are you.

## Provenance

Every field carries a tier: **cited** (a named source in `data/sources/sources.json`),
**harvested** (a tool fetched it from an open dataset), **tradition** (general knowledge
of the trade, hedged in the prose), **inference** (this project reasoning from the above,
and saying so), **field** (somebody stood there — nothing carries it yet).

Records are CC BY 4.0. Place points are OpenStreetMap contributors, ODbL 1.0. Nutrition
figures are USDA FoodData Central SR Legacy, public domain. Pictures carry their own
licences, stated beside each one.

## Build

```
python3 tools/validate.py     # every record must pass
python3 tools/build.py        # records -> build/api
python3 tools/cards.py        # share cards
python3 tools/site.py         # build/site
python3 tools/serve.py        # http://127.0.0.1:8805
```

See `README.txt` for the full pipeline, and `AUTHORING.txt` for how to write a record.


## Licence

Records, prose and pages: CC BY 4.0. Other layers — upstream data,
pictures, tools — keep their own terms, set out in [LICENSE](LICENSE) and [NOTICE.txt](NOTICE.txt).

**Using it.** Attribution is the whole of the condition — copy it, adapt it,
sell it, index it, train on it, and say where it came from.
[Open an issue](https://github.com/NaNoBotCo/pink-box/issues) if something is missing.

---

Contact: Nan · nan@motdang.net · Sponsor: [Ko-fi](https://ko-fi.com/defiantchiangmai) · [Patreon](https://www.patreon.com/nanobotco)

<!-- fleet-roster -->

## Elsewhere from the same publisher

- [Mot Dang](https://motdang.net/) — city directory for Chiang Mai and Chiang Rai
- [The Mae Hong Son Loop](https://nanobotco.github.io/mae-hong-son-loop/) — motorcycling the 600 km loop out of Chiang Mai — curves counted, air measured
- [Muay Thai](https://motdang.net/muay-thai/) — the eight limbs, the thirty named techniques, the ceremony, and every gym on the map
- [wichaa](https://wichaa.net/) — Lanna manuscripts, the amulet market, and the traditions around them
- [Hand Poke](https://nanobotco.github.io/hand-poke/) — 28 traditions of marking skin by hand — the leg-tattoo zone of Burma, the Shan States and Lanna, counted
- [Amulet Atlas](https://nanobotco.github.io/amulet-atlas/) — amulets, charms and talismans worldwide
- [Carolina Barbecue](https://nanobotco.github.io/carolina-barbecue/) — barbecue in North and South Carolina
- [Wing Country](https://nanobotco.github.io/buffalo-wings/) — the American chicken wing
- [Basque Tables](https://nanobotco.github.io/basque-tables/) — Basque dining rooms of California, Nevada and Idaho
- [Pinot Country](https://nanobotco.github.io/pinot-noir/) — pinot noir: the vine, the regions, the cellars
- [Care Abroad](https://nanobotco.github.io/care-abroad/) — treatment across borders, with published prices and their dates
- [Thai Roots](https://nanobotco.github.io/thairoots/) — a root dictionary of Thai, with a word decomposer
- [The index](https://nanobotco.github.io/index/) — every corpus, site and repository, counted
- [Uptake](https://nanobotco.github.io/uptake/) — a field manual on publishing for machines that copy
- [NaNoBotCo](https://nanobotco.github.io/) — the portal
- [ฮักฝรั่ง](https://hakfarang.net/) — เรื่องเงิน วีซ่า และชีวิตกับแฟนฝรั่ง
- [Offrampt](https://offrampt.net/) — turning crypto into spendable local money, Thailand first

All of it, counted: https://nanobotco.github.io/index/ · roster as JSON: https://nanobotco.github.io/index/fleet.json
