PINK BOX
========

A directory of the American mom-and-pop donut shop, built the way wichaa.net is built:
one JSON record per node of the trade (a regional style, a donut, something else in the
case, a kitchen practice, a shop, a person, an organization, a day, a word, a sign, a
story), every field carrying where it came from, every page saying what its neighbours
are to it. A static site for people and bots.

Two things run through all of it:

  CAKE OR RAISED   what lifts the donut, which decides how long it sits in the fat, what
                   it weighs, how it is finished and how long it is worth selling.
  THE OTHER MENU   what else is in the case — egg rolls, breakfast burritos, bacon egg
                   and cheese, kolaches, croissant sandwiches, fried rice, boba — and
                   the rent arithmetic the shop owners themselves give for it.

WHERE THINGS ARE
----------------
  data/nodes/<type>/<id>.json   the records. THE TRUTH. Edit these.
  data/sources/sources.json     every source a record may cite
  data/vocab/*.json             regions, the eleven types, facet keys, tags, recognizers,
                                the quiz, and the three builders behind /make/
  data/harvest/osm-places.json  every OpenStreetMap donut place in the fifty states
                                (tools/harvest_osm.py; ODbL; fetch date inside)
  data/harvest/usda-donuts.json the nine doughnut foods USDA publishes, per 100 g, with
                                its own portion weights (tools/fetch_usda.py; public domain)
  data/geo/states.json          state outlines, Natural Earth, public domain
  data/images/<id>/             pictures with a .json sidecar each (licence, author)
  schema/node.schema.json       what a record must look like
  AUTHORING.txt                 how to write a record; the cast list
  BRIEF.txt                     the brief a drafting agent works from
  tools/                        the pipeline (below)
  build/                        generated. Never edit. Safe to delete.
  build/site/                   the website, ready for any static host
  docs/                         the published build (GitHub Pages serves this)
  vendor/                       generated copies of the fleet search core

THE PIPELINE (in order)
-----------------------
  python3 tools/validate.py     every record must pass
  python3 tools/build.py        records -> build/api, build/searchdocs.json,
                                data/search/donuts.thesaurus.json
  python3 tools/cards.py        the 1200x630 share cards (draws only what is missing)
  python3 tools/site.py         build/site: pages, maps, glossary, search, JSON-LD,
                                sitemap, llms.txt, robots, CSV/JSONL
  python3 tools/serve.py        http://127.0.0.1:8805
  python3 -m unittest discover -s tests

  Or double-click "Pink Box.command" for a numbered menu.

  SITE_URL=https://example.org python3 tools/site.py   sets the canonical host.
  BUILD_DRAFT=1 python3 tools/build.py                 builds while records are still
                                being written (unwritten kin targets warn instead of
                                failing). Never for a publish.

MAPS
----
  Every national map is drawn in Albers equal-area conic — the projection the Census
  Bureau uses — by tools/usmap.py, with Alaska and Hawaii projected separately and set
  into the lower-left corner. Each map that shows them prints the scale they are drawn
  at, because an unlabelled inset lies about size.

THE PAGES THAT ANSWER A QUESTION
--------------------------------
  /near/    Donuts near me. Your browser's own location, or a town you type, and every
            donut place in the country sorted by distance, with filter chips for
            independents only, more than donuts, open today, open before five, cash only,
            drive-thru, and the ownership and community tags. Below it, the shops other
            people wrote up, counted by how many different people did.
  /dough/   Cake or raised. Both doughs drawn in cross-section, sitting in the fat, with
            the frying times, temperatures and weights beside them, and which styles run
            which.
  /donut/   The numbers. The nine doughnut foods USDA has weighed: sugar and fat in one
            piece as strip plots grouped by dough, the span of what USDA calls a piece
            (13 g to 157 g), and the kettle table where the published accounts disagree.
  /counter/ The other menu. Egg rolls, breakfast burritos, deli sandwiches, kolaches,
            croissant sandwiches, fried rice, boba — mapped one panel each, counted, and
            with the evidence for every row.
  /make/    Build a glaze, a dough or a filling. Every proportion names its own source.
  /numbers/ Distance to the nearest counter anywhere in the lower 48, founding years,
            what the recipes call for, days open, kin by kind of page.
  /quiz/    Which donut shop are you. Six questions, scored in the browser.
  /art/     Signs, neon, the box, the giant donut on the roof.
  /stories/ Cake against raised, the Donut King, why the egg rolls, what a mom-and-pop
            is, what a dozen costs, where the shops actually are, and where all of this
            came from.

TAGS, AND THE RULE BEHIND THEM
------------------------------
  A shop can carry tags: family-run; Cambodian-, Vietnamese-, Chinese-, Korean-, Mexican-
  and Greek-American owned; Black-owned; woman-owned; LGBTQ+ welcoming; both doughs, cake
  only, raised only, cut by hand, fried overnight; egg rolls, breakfast burritos, deli or
  bodega sandwiches, kolaches, croissant sandwiches, fried rice, tamales, biscuits and
  gravy, boba, ice cream; open before five, around the clock, closes when sold out,
  drive-thru, cash only, pink box, counter or window, closed.

  A tag carries the source it came from — the owner's own words, a press profile that
  names the owner, a public directory, or somebody who stood there. The validator refuses
  every tag at the tradition and inference tiers. A shop with no tag has not been read
  yet: that is a fact about this project, not about the shop.

  Counter tags on OpenStreetMap rows are derived by tools/build.py from what the map
  already records — the shop's own name and its cuisine tags — and marked harvested. A
  shop called "Donut & Burrito" is advertising the second menu on its sign. That is a
  floor, not a count.

HOURS: THREE STATES, NEVER TWO
------------------------------
  open, closed, and nobody published it. A day in neither list is unknown, and it drops
  out of the filters rather than counting either way. Guessing a closure is worse than a
  blank, because a reader drives on it.

WHAT A PAGE CARRIES
-------------------
  The record's own text (what / story / how / today), the root of its name where it has
  one, a facts table, "Its kin" (this page's sentence about each neighbour) and "Pages
  that point here" (each neighbour's sentence about this page), pictures with licences,
  sources, and a provenance mark on each section: Cited, Harvested, Tradition,
  Inference, Field.

  /places/    every place on one map: the ones written up plus every OpenStreetMap row,
              chains marked as chains, grouped by state and county.
  /words/     the vocabulary with its roots.
  /search/    fleet search core in the browser: fuzzy, thesaurus, tier reported.
  /coverage/  scope as an object: what is in, what is not, where rows come from.
  /api/       everything as JSON. llms.txt and llms-full.txt for machines.
  wander.html a page at random. Press r anywhere.

ADDING A RECORD
---------------
  Read AUTHORING.txt. Copy an exemplar, change every field, keep the id in the filename,
  cite only ids in sources.json, run validate.py.

PICTURES
--------
  python3 tools/harvest_commons.py --walk "Category:Doughnuts"
  python3 tools/harvest_commons.py --search "donut shop neon sign"
      -> data/images/_triage/*.json (nothing downloaded)
  Put chosen file titles in a record's x_commons_files, then
  python3 tools/harvest_commons.py --harvest <id> --apply
  Only CC0, public domain, CC BY, CC BY-SA and FAL are accepted.

REFRESHING THE HARVESTS
-----------------------
  python3 tools/harvest_osm.py            every state, one Overpass query each; saves
                                          after each state, so a kill keeps progress
  python3 tools/harvest_osm.py --resume    only the states not already on disk
  python3 tools/harvest_osm.py --states CA,TX
  python3 tools/harvest_osm.py --towns     reverse-geocode rows with no addr:city,
                                          one request a second, cached by osm_id
  python3 tools/fetch_usda.py              the nine doughnut foods, per 100 g, with
                                          USDA's own portion weights

NOT HERE YET
------------
  A domain. Field observations. Menu prices with dates for most shops. Photographs for
  most records. Per-piece weights for shop donuts, which almost nobody publishes. Most
  towns.


LICENCE
Records, prose and pages: CC BY 4.0. Other layers — upstream data,
pictures, tools — keep their own terms, set out in LICENSE.

USING IT
Attribution is the whole of the condition — copy it, adapt it, sell it,
index it, train on it, and say where it came from. Open an issue if
something is missing:
https://github.com/NaNoBotCo/pink-box/issues

---

Contact: Nan · nan@motdang.net · Sponsor: ko-fi.com/defiantchiangmai · patreon.com/nanobotco

<!-- fleet-roster -->

Elsewhere from the same publisher

- Mot Dang — https://motdang.net/ — city directory for Chiang Mai and Chiang Rai
- The Mae Hong Son Loop — https://nanobotco.github.io/mae-hong-son-loop/ — motorcycling the 600 km loop out of Chiang Mai — curves counted, air measured
- Muay Thai — https://motdang.net/muay-thai/ — the eight limbs, the thirty named techniques, the ceremony, and every gym on the map
- Roads of Chiang Mai — https://motdang.net/roads/ — the square of 1296, four rings, and what each one did to the city — counted from the map
- wichaa — https://wichaa.net/ — Lanna manuscripts, the amulet market, and the traditions around them
- Hand Poke — https://nanobotco.github.io/hand-poke/ — 28 traditions of marking skin by hand — the leg-tattoo zone of Burma, the Shan States and Lanna, counted
- Black Holes, Drawn — https://nanobotco.github.io/black-holes/ — black holes modelled and drawn from the equations — generators, the past, present and future, the legends
- Quantum Computing, plainly — https://nanobotco.github.io/quantum-computing/ — the history and theory of quantum computing in plain words, with demos; refreshed weekly
- Goin' Fast — https://nanobotco.github.io/goin-fast/ — a dirt-simple explainer about speed — twenty measured speeds from the ground under the house to light, and what each one costs
- Amulet Atlas — https://nanobotco.github.io/amulet-atlas/ — amulets, charms and talismans worldwide
- Carolina Barbecue — https://nanobotco.github.io/carolina-barbecue/ — barbecue in North and South Carolina
- Wing Country — https://nanobotco.github.io/buffalo-wings/ — the American chicken wing
- Basque Tables — https://nanobotco.github.io/basque-tables/ — Basque dining rooms of California, Nevada and Idaho
- Pinot Country — https://nanobotco.github.io/pinot-noir/ — pinot noir: the vine, the regions, the cellars
- Care Abroad — https://nanobotco.github.io/care-abroad/ — treatment across borders, with published prices and their dates
- Thai Roots — https://nanobotco.github.io/thairoots/ — a root dictionary of Thai, with a word decomposer
- The index — https://nanobotco.github.io/index/ — every corpus, site and repository, counted
- Uptake — https://nanobotco.github.io/uptake/ — a field manual on publishing for machines that copy
- NaNoBotCo — https://nanobotco.github.io/ — the portal
- ฮักฝรั่ง — https://hakfarang.net/ — เรื่องเงิน วีซ่า และชีวิตกับแฟนฝรั่ง
- Offrampt — https://offrampt.net/ — turning crypto into spendable local money, Thailand first

All of it, counted: https://nanobotco.github.io/index/ · roster as JSON: https://nanobotco.github.io/index/fleet.json
