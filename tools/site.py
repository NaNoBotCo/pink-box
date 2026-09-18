#!/usr/bin/env python3
"""site.py — build/api → build/site: a static site people and bots can both read.

People: a 1997-directory front (Term (count) links, hierarchy on the page), one page per
node with its kin said in both directions, an inline SVG map of every place, a glossary
with roots, large type, high contrast, theme-aware, motion gated behind
prefers-reduced-motion, no external requests.

Bots: JSON-LD on every page, robots.txt that ALLOWS everything and says so with
Content-Signal, sitemap.xml with lastmod, llms.txt and llms-full.txt, Atom feed,
OpenSearch description, CSV + JSONL dumps, the whole /api tree.

    python3 tools/site.py                          # SITE_URL defaults to the Pages address
    SITE_URL=https://example.org python3 tools/site.py
"""
from __future__ import annotations

import csv
import html
import json
import math
import os
import random
import re
import shutil
import sys
import urllib.parse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BUILD, DATA, GEO, HARVEST, IMAGES, ROOT, SEARCH_CORE, TIER_LABEL, TYPES, VENDOR, jload  # noqa: E402
import pages  # noqa: E402
import usmap  # noqa: E402
import viz  # noqa: E402

DOUGH_KINDS = {k: v for k, _, v, _ in pages.DOUGH_STYLES}

SITE = BUILD / "site"
API = BUILD / "api"
SITE_URL = os.environ.get("SITE_URL", "https://nanobotco.github.io/pink-box").rstrip("/")
SITE_NAME = "Pink Box"
TAGLINE = "cake or raised, egg rolls in the case, and who's been up since two"
DATA_LICENSE = "https://creativecommons.org/licenses/by/4.0/"   # the records' own licence — Nan's call; default CC BY 4.0
AUTHOR = {"@type": "Person", "name": "NaN", "url": "https://wichaa.net"}
def E(x) -> str:
    """html.escape, but a null field is a blank rather than a crash — a JSON field is
    null here when nobody published the thing, which is a state the site prints."""
    return html.escape("" if x is None else str(x))
PATH_OF = {"style": "style", "donut": "donut", "dish": "dish", "kitchen": "kitchen", "place": "place", "person": "person", "org": "org", "event": "event", "term": "word", "art": "art", "story": "story"}
DIR_OF = {"style": "styles", "donut": "donuts", "dish": "dishes", "kitchen": "kitchen", "place": "places", "person": "people", "org": "organizations", "event": "events", "term": "words", "art": "art", "story": "stories"}
STATE_NAME = {s["iso"][3:]: s["name"] for s in jload(GEO / "states.json")["states"]}


def clip(text: str, n: int) -> str:
    """Cut at a word, and say that it was cut."""
    t = (text or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"


def rel(depth: int) -> str:
    return "../" * depth


def url_of(r: dict) -> str:
    return f"{PATH_OF[r['type']]}/{r['id']}/"


def img_src(im: dict, depth: int) -> str:
    return f"{rel(depth)}images/{im['file']}"


CSS = """
:root{--bg:#fff5fa;--panel:#ffffff;--ink:#2a1420;--mute:#78596a;--line:#ffd0e4;--donut:#d6136a;--smoke:#5b3220;--gold:#6d2bd9;--lemon:#c98a00;--hot:#a50f50;--blue:#0f6fc4;--celery:#0d8f63;--focus:#0f5fd1;--chip:#ffe6f2;--mint:#0d8f63;--cyan:#0f8fb8;--sprinkle:#ffd23f;
  /* A donut shop letters its own window in fat caps and paints the rest bubblegum. Headings
     take a rounded sign face, labels take the fattest caps on the machine, and the reading
     text stays a plain humanist sans. All of it sits on the reader's machine already. */
  --display:"Arial Rounded MT Bold","Helvetica Rounded",Avenir,"Avenir Next","Trebuchet MS",sans-serif;
  --sign:"Arial Black","Helvetica Neue Black",Impact,Haettenschweiler,"Franklin Gothic Heavy",sans-serif;
  --body:"Avenir Next",Avenir,"Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif;
  --ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#190e15;--panel:#251622;--ink:#ffeef7;--mute:#cba6bb;--line:#43283a;--donut:#ff6faa;--smoke:#e3c3ad;--gold:#c79bff;--lemon:#ffd25e;--hot:#ffa1c7;--blue:#79c2ff;--celery:#4ad6a1;--focus:#8ab4f8;--chip:#33202c;--mint:#4ad6a1;--cyan:#5ed0ee;--sprinkle:#ffd23f}}
:root[data-theme="dark"]{--bg:#190e15;--panel:#251622;--ink:#ffeef7;--mute:#cba6bb;--line:#43283a;--donut:#ff6faa;--smoke:#e3c3ad;--gold:#c79bff;--lemon:#ffd25e;--hot:#ffa1c7;--blue:#79c2ff;--celery:#4ad6a1;--focus:#8ab4f8;--chip:#33202c;--mint:#4ad6a1;--cyan:#5ed0ee;--sprinkle:#ffd23f}
*{box-sizing:border-box}html{font-size:19px;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);line-height:1.62;font-size:1.02rem}
a{color:var(--donut);text-decoration-thickness:.07em;text-underline-offset:.16em}a:hover{color:var(--hot)}
a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid var(--focus);outline-offset:2px;border-radius:4px}
header.top{border-bottom:1px solid var(--line);padding:.7rem 1rem;max-width:66rem;margin:0 auto;display:flex;gap:.6rem 1.2rem;flex-wrap:wrap;align-items:baseline}
header.top .brand{font-weight:700;text-decoration:none;color:var(--ink);letter-spacing:.01em}header.top .brand b{color:var(--donut)}
nav.crumbs{font-size:.84rem;color:var(--mute);font-family:var(--ui)}nav.crumbs a{text-decoration:none}nav.crumbs a:hover{text-decoration:underline}
main{max-width:66rem;margin:0 auto;padding:1.2rem 1rem 4rem}
h1{font-family:var(--display);font-size:clamp(2rem,4.4vw,2.9rem);line-height:1.08;margin:.5rem 0 .3rem;font-weight:700;letter-spacing:-.005em}h1 .kind{display:block;font-size:.76rem;color:var(--gold);text-transform:uppercase;letter-spacing:.22em;font-family:var(--sign);margin-bottom:.5rem}
h2{font-family:var(--display);font-size:1.32rem;margin:1.8rem 0 .5rem;border-bottom:2px solid var(--line);padding-bottom:.25rem;font-weight:700}
h3{font-family:var(--display);font-size:1.06rem;margin:1rem 0 .3rem;font-weight:700}
.said{font-style:italic;color:var(--mute);margin:.2rem 0 .8rem}.lede{font-size:1.12rem;margin:.2rem 0 1rem}.mute{color:var(--mute)}
p{margin:.55rem 0}.prose p{margin:.7rem 0}
.dir{display:grid;grid-template-columns:repeat(auto-fill,minmax(19rem,1fr));gap:1.3rem 2.4rem;align-items:start;margin-top:.8rem}
.dir section{margin:0}.dir h2{margin:.2rem 0 .3rem;border:0;font-size:1.14rem;font-family:var(--display)}.dir h2 a{text-decoration:none;color:var(--ink)}.dir h2 a:hover{color:var(--donut)}
.dir ul{list-style:none;margin:0;padding:0 0 0 .7rem;border-left:2px solid var(--line)}.dir li{margin:.14rem 0}.dir li.sub{padding-left:.9rem;font-size:.95rem}
.count{color:var(--mute);font-size:.85em;font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
.chip{display:inline-block;background:var(--chip);border:1px solid var(--line);border-radius:999px;padding:.05rem .6rem;font-size:.78rem;margin:.1rem .25rem .1rem 0;color:var(--ink);font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
.tier-cited{border-color:var(--focus)}.tier-harvested{border-color:var(--smoke)}.tier-tradition{border-color:var(--gold)}.tier-inference{border-style:dashed}.tier-field{border-color:var(--donut)}
table{border-collapse:collapse;width:100%;margin:.4rem 0 1rem;font-size:.95rem}th,td{text-align:left;vertical-align:top;padding:.45rem .5rem;border-bottom:1px solid var(--line)}th{width:28%;color:var(--mute);font-weight:600}
.kin{display:grid;grid-template-columns:repeat(auto-fill,minmax(17rem,1fr));gap:.9rem}.kin a.card{display:block;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:.8rem .95rem;text-decoration:none;color:var(--ink);position:relative}
.kin a.card b{display:block;font-size:1.03rem;color:var(--donut);font-family:var(--display);font-weight:700}.kin a.card small{display:block;font-size:.7rem;color:var(--gold);text-transform:uppercase;letter-spacing:.18em;font-family:var(--sign)}.kin a.card span{display:block;margin-top:.3rem;font-size:.92rem;color:var(--ink)}
.kin a.card:hover b{color:var(--hot)}
figure{margin:0 0 1rem;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:.6rem}figure img{width:100%;height:auto;max-height:32rem;object-fit:contain;border-radius:8px;display:block}figcaption{font-size:.8rem;color:var(--mute);margin-top:.4rem;font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(12rem,1fr));gap:.7rem}.gallery figure{margin:0}
/* A photograph across the top of the front page is a band, not a wall: crop it so the
   name and the map still land on the first screen. */
.hero-shot.wide{margin:0 0 1.1rem}.hero-shot.wide img{max-height:none;aspect-ratio:21/6;object-fit:cover;object-position:center 62%}
@media(max-width:760px){.hero-shot.wide img{aspect-ratio:16/9}}
.hero-shot img{max-height:26rem;object-fit:cover}
.hero{display:grid;grid-template-columns:1.1fr .9fr;gap:1.6rem;align-items:center;margin:.6rem 0 1.4rem}.hero h1{font-family:var(--display);font-size:clamp(2.3rem,6vw,3.7rem);letter-spacing:-.01em}.hero .sub{font-size:1.15rem;color:var(--mute);font-style:italic;max-width:32rem}
@media(max-width:760px){.hero{grid-template-columns:1fr}html{font-size:18px}}
.mapwrap{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:.5rem}.mapwrap svg{width:100%;height:auto;display:block}
.facts{display:flex;flex-wrap:wrap;gap:.8rem;margin:.6rem 0 1.2rem}.fact{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:.7rem 1rem;min-width:8rem;text-align:center}.fact .n{font-family:var(--display);font-size:2rem;font-weight:700;line-height:1}.fact .l{font-size:.76rem;color:var(--mute);margin-top:.28rem;font-family:var(--sign);text-transform:uppercase;letter-spacing:.09em}
.search{display:flex;gap:.5rem;margin:.6rem 0 1rem}.search input{flex:1;font:inherit;font-size:1.1rem;padding:.6rem .8rem;border:2px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink)}.search button{font:inherit;padding:.6rem 1rem;border-radius:10px;border:2px solid var(--donut);background:var(--donut);color:#fff;cursor:pointer}
.tierline{font-size:.9rem;color:var(--mute);margin:.2rem 0 .8rem}.legend{font-size:.85rem;color:var(--mute);border-top:1px solid var(--line);margin-top:2rem;padding-top:.6rem}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:1rem;align-items:start}
.card .thumb{width:100%;aspect-ratio:16/9;object-fit:cover;object-position:88% center;border-radius:9px;margin-bottom:.55rem;display:block;background:var(--chip)}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:.9rem}.card a.t{font-family:var(--display);font-weight:700;text-decoration:none;font-size:1.06rem}.card p{margin:.3rem 0 0;font-size:.9rem;color:var(--mute)}
footer{max-width:66rem;margin:0 auto;padding:1rem;color:var(--mute);font-size:.85rem;border-top:1px solid var(--line);font-family:-apple-system,"Segoe UI",Roboto,sans-serif}.bots a{margin-right:.7rem}
.btn{display:inline-block;padding:.55rem 1.05rem;border-radius:999px;background:var(--donut);color:#fff;text-decoration:none;font-weight:700;border:2px solid var(--donut);font-family:var(--sign);font-size:.92rem;letter-spacing:.03em}.btn.ghost{background:transparent;color:var(--ink);border-color:var(--line)}.btn:hover{color:#fff;filter:brightness(1.08)}.btn.ghost:hover{color:var(--ink);border-color:var(--donut)}
.cta{display:flex;gap:.6rem;flex-wrap:wrap;margin:.8rem 0}
.etym{background:var(--panel);border-left:4px solid var(--lemon);border-radius:0 12px 12px 0;padding:.7rem 1rem;margin:.8rem 0}
.wander{font-size:.85rem;color:var(--mute)}
.pl-list{columns:2;column-gap:2.4rem;font-size:.95rem}.pl-list h3{break-after:avoid;margin:.6rem 0 .2rem}.pl-list ul{margin:0 0 .5rem;padding-left:1rem}@media(max-width:700px){.pl-list{columns:1}}
mark.tier{background:transparent;color:var(--mute);font-style:italic}
.whenbox{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:.9rem 1rem;margin:.4rem 0 1rem}
.whenbox .hrs{margin:.55rem 0 0;font-size:.95rem}
.whenbox .hrs.sold{color:var(--donut);font-weight:600}
.two-up{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1.4rem 0}@media(max-width:700px){.two-up{grid-template-columns:1fr}}
.pitch{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:1rem 1.2rem}
.tagrow{display:flex;flex-wrap:wrap;gap:.35rem;margin:.5rem 0 .3rem}
.tagrow a.tg,.tagrow span.tg{display:inline-flex;align-items:center;gap:.3rem;background:var(--chip);border:1px solid var(--line);border-radius:999px;padding:.15rem .7rem;font-size:.84rem;font-family:-apple-system,"Segoe UI",Roboto,sans-serif;text-decoration:none;color:var(--ink)}
.tagrow a.tg:hover{border-color:var(--donut)}
.tagrow .tg.own{border-color:var(--gold)}.tagrow .tg.welcome{border-color:#9b59b6}.tagrow .tg.pit{border-color:var(--donut)}
.acc{display:flex;flex-wrap:wrap;gap:.4rem;margin:.3rem 0 .6rem;font-size:.86rem;font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
.acc b{color:var(--gold)}
.recipe{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--gold);border-radius:0 12px 12px 0;padding:.8rem 1rem;margin:.8rem 0}
.recipe h3{margin:.1rem 0 .2rem;font-size:1.02rem}
.recipe .src{font-size:.82rem;color:var(--mute);font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
.recipe .txt{white-space:pre-wrap;margin:.5rem 0 0;font-size:.97rem}
.recipe ul{margin:.4rem 0 0;padding-left:1.1rem}
.sect{margin:1.2rem 0}
.gal2{display:grid;grid-template-columns:repeat(auto-fill,minmax(14rem,1fr));gap:.8rem;margin:.6rem 0}
.gal2 figure{margin:0}

/* ------------------------------------------------------------------ candy */
/* Sprinkles, drawn with gradients so the page asks nobody for a picture. */
body{background-image:
  radial-gradient(circle at 12% 8%, color-mix(in srgb,var(--sprinkle) 55%,transparent) 0 3px, transparent 4px),
  radial-gradient(circle at 78% 14%, color-mix(in srgb,var(--cyan) 45%,transparent) 0 3px, transparent 4px),
  radial-gradient(circle at 33% 62%, color-mix(in srgb,var(--donut) 32%,transparent) 0 3px, transparent 4px),
  radial-gradient(circle at 88% 78%, color-mix(in srgb,var(--mint) 40%,transparent) 0 3px, transparent 4px),
  radial-gradient(circle at 58% 36%, color-mix(in srgb,var(--gold) 30%,transparent) 0 2px, transparent 3px);
  background-size:420px 380px;background-attachment:fixed}
header.top{background:var(--panel);border-bottom:3px solid var(--donut)}
header.top .brand{font-family:var(--display);font-size:1.25rem;letter-spacing:-.01em}
header.top .brand b{color:var(--donut)}
h1{letter-spacing:-.02em}
h1 .kind{color:var(--gold)}
h2{border-bottom:3px dotted var(--line)}
.btn{border-width:3px;box-shadow:3px 3px 0 var(--ink);text-transform:uppercase}
.btn.ghost{background:var(--panel);box-shadow:3px 3px 0 var(--line)}
.btn:active{transform:translate(2px,2px);box-shadow:1px 1px 0 var(--ink)}
.card,.kin a.card,.fact,.pitch,.whenbox,.mapwrap,figure,.recipe{border-width:2px;border-style:solid;border-color:var(--line)}
.kin a.card{box-shadow:4px 4px 0 var(--chip)}
.fact{box-shadow:4px 4px 0 var(--chip);border-radius:16px}
.fact .n{color:var(--donut)}
.fact .l{color:var(--mute)}
.chip{border-width:2px}
.dir h2 a:hover{color:var(--donut)}
.dir ul{border-left:3px solid var(--line)}
.etym{border-left:5px solid var(--gold);background:var(--chip)}
.recipe{border-left:5px solid var(--sprinkle)}
.search input{border-width:3px;border-color:var(--donut)}
.search button{box-shadow:3px 3px 0 var(--ink);text-transform:uppercase;font-family:var(--sign);letter-spacing:.04em}
.tagrow a.tg,.tagrow span.tg{border-width:2px;font-weight:600}
.tagrow .tg.own{border-color:var(--gold)}.tagrow .tg.community{border-color:var(--cyan)}
.tagrow .tg.counter{border-color:var(--mint);background:color-mix(in srgb,var(--mint) 12%,var(--panel))}
.tagrow .tg.kitchen{border-color:var(--donut)}
/* The two doughs get one colour each and keep it everywhere on the site. */
.dough-yeast{color:var(--donut)}.dough-cake{color:var(--blue)}
.pill{display:inline-block;font-family:var(--sign);text-transform:uppercase;letter-spacing:.06em;font-size:.72rem;padding:.12rem .55rem;border-radius:999px;border:2px solid currentColor;margin-right:.35rem}
.pill.yeast{color:var(--donut)}.pill.cake{color:var(--blue)}.pill.choux{color:var(--gold)}.pill.other{color:var(--mute)}
.hero h1{text-shadow:4px 4px 0 var(--chip)}
.boxwrap{background:var(--chip);border:3px solid var(--donut);border-radius:18px;padding:1rem;margin:1rem 0}
.legend{border-top:3px dotted var(--line)}
footer{border-top:3px dotted var(--line)}
@media (prefers-reduced-motion: no-preference){.kin a.card,.card,.fact{transition:transform .18s ease,box-shadow .18s ease}.kin a.card:hover,.card:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(0,0,0,.09)}.btn{transition:transform .15s ease}.btn:hover{transform:scale(1.04)}.search input{transition:box-shadow .2s}.search input:focus{box-shadow:0 0 0 4px color-mix(in srgb,var(--donut) 22%,transparent)}.mapwrap circle.p{transition:r .15s ease}.mapwrap circle.p:hover{r:6}}
"""


def page(title: str, body: str, depth: int, desc: str = "", jsonld: list | None = None, canonical: str = "", extra_head: str = "",
         og_image: str = "", alt_json: str = "", og_alt: str = "", og_type: str = "website", card: str = "", share_title: str = "") -> str:
    r = rel(depth)
    if card and (CARDS_DIR / f"{card}.jpg").exists():
        og_image = f"{SITE_URL}/cards/{card}.jpg"
    ld = "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>' for o in (jsonld or []))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc[:300])}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="color-scheme" content="light dark">
<meta property="og:site_name" content="{E(SITE_NAME)}"><meta property="og:locale" content="en_US">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc[:200])}"><meta property="og:type" content="{E(og_type)}">
{f'<meta property="og:image" content="{E(og_image)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:type" content="image/jpeg"><meta property="og:image:alt" content="{E(og_alt or title)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{E(og_image)}"><meta name="twitter:image:alt" content="{E(og_alt or title)}"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc[:200])}">' if og_image else ''}
{f'<link rel="canonical" href="{E(canonical)}">' if canonical else ''}
{f'<link rel="alternate" type="application/json" href="{E(alt_json)}">' if alt_json else ''}
<link rel="manifest" href="{r}manifest.webmanifest">
<meta name="theme-color" content="#d6136a">
<link rel="icon" href="{r}icon.svg" type="image/svg+xml">
<link rel="search" type="application/opensearchdescription+xml" title="{E(SITE_NAME)}" href="{r}opensearch.xml">
<link rel="alternate" type="application/atom+xml" title="{E(SITE_NAME)} updates" href="{r}feed.xml">
{extra_head}
<style>{CSS}{SHARE_CSS}{viz.DAY_CSS}</style>
{ld}
</head>
<body>
<header class="top"><a class="brand" href="{r}index.html">Pink <b>Box</b></a>
<nav class="crumbs"><a href="{r}index.html">Everything</a> · <a href="{r}near/index.html">Near me</a> · <a href="{r}places/index.html">Map</a> · <a href="{r}donut/index.html">Donuts</a> · <a href="{r}dough/index.html">Cake or raised</a> · <a href="{r}counter/index.html">The counter</a> · <a href="{r}make/index.html">Make some</a> · <a href="{r}numbers/index.html">Numbers</a> · <a href="{r}art/index.html">Signs</a> · <a href="{r}stories/index.html">Stories</a> · <a href="{r}quiz/index.html">Quiz</a> · <a href="{r}search/index.html">Search</a> · <a href="{r}words/index.html">Words</a> · <a href="{r}sources/index.html">Sources</a> · <a href="{r}coverage/index.html">Coverage</a> · <a href="{r}api/index.json">API</a> · <a href="{r}llms.txt">llms.txt</a> · <a class="wander" href="{r}wander.html" title="a page at random">🎲 Wander</a></nav></header>
<main>
{body}
{share_row(canonical, share_title or title) if canonical else ""}
</main>
<script>document.addEventListener("keydown",function(e){{if(e.key==="r"&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&!/input|textarea/i.test(e.target.tagName))location.href="{r}wander.html"}});</script>
<footer>
<div class="bots">For the machines: <a href="{r}api/nodes.json">nodes.json</a> <a href="{r}api/places.json">places.json</a> <a href="{r}api/kin.json">kin.json</a> <a href="{r}nodes.jsonl">nodes.jsonl</a> <a href="{r}nodes.csv">nodes.csv</a> <a href="{r}llms-full.txt">llms-full.txt</a> <a href="{r}sitemap.xml">sitemap.xml</a> <a href="{r}feed.xml">feed.xml</a> <a href="{r}api/coverage.json">coverage</a> <a href="{r}api/sources.json">sources</a></div>
<p>Records licensed <a href="{DATA_LICENSE}">CC BY 4.0</a>. Place points from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>, ODbL. Pictures carry their own licences, stated beside each one. Every field says where it came from.</p>
</footer>
</body>
</html>
"""


# ------------------------------------------------------------------ helpers

def tier_chip(t: dict) -> str:
    tier = (t or {}).get("tier", "")
    if not tier:
        return ""
    lab = {"cited": "Cited", "harvested": "Harvested", "tradition": "Tradition", "inference": "Inference", "field": "Field"}.get(tier, tier)
    src = (t or {}).get("source", "")
    note = (t or {}).get("note", "")
    return f'<span class="chip tier-{E(tier)}" title="{E((src + " — " if src else "") + note)}">{E(lab)}{(" · " + E(src[2:])) if src else ""}</span>'


def marks(text: str) -> str:
    """Escape, then render *Tradition holds —* / *Inference —* as quiet italics (one line, no paragraphs)."""
    return re.sub(r"\*([^*]+)\*", r'<mark class="tier">\1</mark>', E(text or ""))


def prose(text: str) -> str:
    """Paragraphs; *Tradition holds —* / *Inference —* marks rendered as quiet italics."""
    out = []
    for para in re.split(r"\n\s*\n", (text or "").strip()):
        p = E(para.strip())
        p = re.sub(r"\*([^*]+)\*", r'<mark class="tier">\1</mark>', p)
        out.append(f"<p>{p}</p>")
    return "".join(out)


def name_link(r: dict, depth: int) -> str:
    return f'<a href="{rel(depth)}{url_of(r)}index.html">{E(r["names"]["name"])}</a>'


def group_key(r: dict, key: str):
    node = r
    for part in key.split("."):
        node = (node or {}).get(part) if isinstance(node, dict) else None
    if key == "facets.letter":
        return (r["names"]["name"][:1] or "?").upper()
    if isinstance(node, list):
        return node[0] if node else None
    return node


GROUP_LABEL = dict(STATE_NAME)
GROUP_LABEL.update({
    "us": "Coast to coast", "—": "Other", "unknown": "State not tagged",
    # dough, the axis the case is arranged on
    "yeast": "Raised", "cake": "Cake", "choux": "Choux", "potato": "Potato",
    "sourdough": "Sourdough", "both": "Both doughs", "other": "Other",
    # what else is on the counter
    "breakfast": "Breakfast", "savory": "Savoury", "sweet": "Sweet", "drink": "Drinks", "side": "Sides",
    # out back
    "mix": "Mixing", "raise": "The raise", "cut": "Cutting", "fry": "Frying", "finish": "Finishing",
    "hold": "Holding", "tool": "Tools", "shift": "The shift",
    # signs
    "sign": "Signs", "neon": "Neon", "mascot": "Mascots", "mural": "Murals", "box": "Boxes",
    "print": "Prints", "photograph": "Photographs",
    # stories
    "essay": "Essays", "map": "Maps explained", "quiz": "Games", "resources": "Where it came from",
    # people
    "fryer": "Fryers", "founder": "Founders", "family": "Families", "writer": "Writers", "scholar": "Scholars",
    "organizer": "Organizers", "inventor": "Inventors", "supplier": "Suppliers", "cook": "Cooks",
    "baker": "Bakers", "owner": "Owners", "broadcaster": "Broadcasters"})


def directory_sections(recs: list[dict], types: dict, depth: int, limit: int | None = None) -> str:
    out = []
    for t in types["entries"]:
        rs = [r for r in recs if r["type"] == t["key"]]
        if not rs:
            continue
        groups: dict = {}
        for r in rs:
            g = group_key(r, t["group_by"]) or "—"
            groups.setdefault(g, []).append(r)
        lis = []
        for g, members in sorted(groups.items(), key=lambda kv: (kv[0] == "—", str(kv[0]))):
            members.sort(key=lambda r: (r["names"].get("sort") or r["names"]["name"]).lower())
            if len(groups) > 1:
                lis.append(f'<li><b>{E(GROUP_LABEL.get(g, str(g)))}</b> <span class="count">({len(members)})</span></li>')
            for r in (members if limit is None else members[:limit]):
                lis.append(f'<li class="{"sub" if len(groups) > 1 else ""}">{name_link(r, depth)}</li>')
            if limit is not None and len(members) > limit:
                lis.append(f'<li class="sub"><a href="{rel(depth)}{DIR_OF[t["key"]]}/index.html">… all {len(members)}</a></li>')
        out.append(f'<section><h2><a href="{rel(depth)}{DIR_OF[t["key"]]}/index.html">{E(t["name"])}</a> <span class="count">({len(rs)})</span></h2><p class="mute" style="margin:.1rem 0 .4rem;font-size:.9rem">{E(t["blurb"])}</p><ul>{"".join(lis)}</ul></section>')
    return f'<div class="dir">{"".join(out)}</div>'


# ------------------------------------------------------------------ the map

def map_svg(places: list[dict], recs_by_id: dict, depth: int, width=760) -> str:
    """Inline SVG: fifty states in Albers equal-area, one dot per INDEPENDENT donut place;
    places written up here are donut-coloured and link to their page, OpenStreetMap rows are
    smoke. Chain locations are dropped before the map is drawn — two thirds of the rows in
    the harvest are one company's, and a map of them is a map of that company, not of this
    subject. The count and the way back to them is printed under every map that does it.
    Alaska and Hawaii sit in the corner at the reduced scale the caption names."""
    g = usmap.load()
    fit = usmap.fit_states(g, width * 0.88, pad=10)
    w, h = width, fit["h"] + 8
    paths = []
    for iso, name, d in usmap.state_paths(g, fit):
        paths.append(f'<path class="st" d="{d}"><title>{E(name)}</title></path>')
    dots = []
    for p in places:
        if p.get("lat") is None or p.get("chain"):
            continue
        x, y = usmap.project(p["lon"], p["lat"], fit)
        if not (0 <= x <= w and 0 <= y <= h):
            continue
        label = E(p["name"]) + (f" · {E(p['city'])}" if p.get("city") else "") + (f", {p['state']}" if p.get("state") else "")
        if p["curated"]:
            dots.append(f'<a href="{rel(depth)}{p["url"]}index.html"><circle class="p c" cx="{x:.1f}" cy="{y:.1f}" r="4.6"><title>{label}</title></circle></a>')
        else:
            dots.append(f'<a href="https://www.openstreetmap.org/?mlat={p["lat"]}&amp;mlon={p["lon"]}#map=16/{p["lat"]}/{p["lon"]}" rel="noopener"><circle class="p o" cx="{x:.1f}" cy="{y:.1f}" r="2.2"><title>{label} (OpenStreetMap)</title></circle></a>')
    # where a style is spoken; placed at the city it is named for
    labels = [(-118.24, 34.05, "Los Angeles · the pink box", "start", 16),
              (-95.37, 29.76, "Houston · kolaches", "middle", 16),
              (-106.65, 35.08, "Albuquerque · burritos", "middle", -9),
              (-87.63, 41.84, "Chicago · pączki", "middle", -9),
              (-73.94, 40.73, "New York · bacon egg and cheese", "end", -10),
              (-80.24, 36.10, "Winston-Salem · the hot light", "end", 16),
              (-90.07, 29.95, "New Orleans · beignets", "middle", 16),
              (-122.68, 45.52, "Portland · novelty", "start", -7),
              (-157.86, 21.31, "Honolulu · malasadas", "start", 14)]
    lab = []
    for lon, lat, text, anchor, dy in labels:
        x, y = usmap.project(lon, lat, fit)
        lab.append(f'<text class="lab" text-anchor="{anchor}" x="{x:.1f}" y="{y + dy:.1f}">{E(text)}</text>')
    inset = (f'<text class="ins" x="{fit["pad"] + 4:.0f}" y="{h - 4:.0f}">Alaska {fit["ak"]["rel"]*100:.0f}% · '
             f'Hawaii {fit["hi"]["rel"]*100:.0f}% of scale</text>')
    style = ("<style>.st{fill:#efe7d4;stroke:#a8a090;stroke-width:.8}"
             ".p.c{fill:#cf4a1e;stroke:#fff;stroke-width:1}.p.o{fill:#6b6257;opacity:.5}"
             ".lab{font:700 12px Futura,'Century Gothic','Avenir Next',sans-serif;fill:#3f3a34;paint-order:stroke;stroke:#f7f4ec;stroke-width:3.4px;stroke-linejoin:round}"
             ".ins{font:600 10px -apple-system,'Segoe UI',Roboto,sans-serif;fill:#6a6257}"
             "@media (prefers-color-scheme: dark){.st{fill:#2a251d;stroke:#5d5443}.p.o{fill:#b3a898}"
             ".lab{fill:#f0e9db;stroke:#15130f}.ins{fill:#b2a998}}</style>")
    return (f'<svg viewBox="0 0 {w} {h:.0f}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Map of the United States with every donut place as a dot">'
            f'{style}{"".join(paths)}{"".join(dots)}{"".join(lab)}{inset}</svg>')


# ------------------------------------------------------------------ pages

def node_jsonld(r: dict) -> list:
    url = f"{SITE_URL}/{url_of(r)}"
    base = {"@context": "https://schema.org", "url": url, "name": r["names"]["name"], "description": r["blurb"], "inLanguage": "en",
            "isPartOf": {"@type": "Dataset", "name": SITE_NAME, "url": SITE_URL + "/"}, "license": DATA_LICENSE, "dateModified": r["updated"]}
    if r.get("names", {}).get("aliases"):
        base["alternateName"] = r["names"]["aliases"]
    if r["type"] == "place":
        a = r.get("address") or {}
        g = r.get("geo") or {}
        base.update({"@type": "Bakery", "servesCuisine": "Donuts"})
        if a:
            base["address"] = {"@type": "PostalAddress", "streetAddress": a.get("street", ""), "addressLocality": a.get("city", ""), "addressRegion": a.get("state", ""), "postalCode": a.get("postcode", ""), "addressCountry": "US"}
        if g:
            base["geo"] = {"@type": "GeoCoordinates", "latitude": g["lat"], "longitude": g["lon"]}
        if r.get("links"):
            base["sameAs"] = [l["url"] for l in r["links"]]
    elif r["type"] == "person":
        base.update({"@type": "Person"})
        if r.get("links"):
            base["sameAs"] = [l["url"] for l in r["links"]]
    elif r["type"] == "org":
        base.update({"@type": "Organization"})
        if r.get("links"):
            base["sameAs"] = [l["url"] for l in r["links"]]
    elif r["type"] == "event":
        base.update({"@type": "Event", "eventSchedule": (r.get("facets") or {}).get("when", "")})
        g = r.get("geo") or {}
        if g:
            base["location"] = {"@type": "Place", "geo": {"@type": "GeoCoordinates", "latitude": g["lat"], "longitude": g["lon"]}}
    elif r["type"] == "term":
        base.update({"@type": "DefinedTerm", "inDefinedTermSet": f"{SITE_URL}/words/"})
    else:
        base.update({"@type": "DefinedTerm", "inDefinedTermSet": f"{SITE_URL}/{DIR_OF[r['type']]}/"})
    out = [base, {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": DIR_OF[r["type"]].replace("-", " ").title(), "item": f"{SITE_URL}/{DIR_OF[r['type']]}/"},
        {"@type": "ListItem", "position": 3, "name": r["names"]["name"], "item": url}]}]
    # a recipe a reader may actually cook is worth saying so in the machine layer
    for i, rc in enumerate(r.get("recipes", []), 1):
        lic = (rc.get("license") or "").strip()
        rec_ld = {"@context": "https://schema.org", "@type": "Recipe", "name": rc.get("title", r["names"]["name"]),
                  "url": f"{url}#recipe-{i}", "isPartOf": {"@type": "WebPage", "@id": url},
                  "recipeCuisine": "American", "inLanguage": "en"}
        if rc.get("ingredients"):
            rec_ld["recipeIngredient"] = rc["ingredients"]
        if rc.get("text"):
            steps = [x.strip() for x in re.split(r"(?<=[.;])\s{1,}(?=[A-Z])", rc["text"]) if len(x.strip()) > 12]
            rec_ld["recipeInstructions"] = ([{"@type": "HowToStep", "text": x} for x in steps] if len(steps) > 1
                                            else rc["text"])
        if rc.get("author") or rc.get("book"):
            rec_ld["author"] = {"@type": "Person" if rc.get("author") else "Organization", "name": rc.get("author") or rc.get("book")}
        if rc.get("book"):
            rec_ld["isBasedOn"] = {"@type": "Book", "name": rc["book"], **({"datePublished": str(rc["year"])} if rc.get("year") else {})}
        if rc.get("year"):
            rec_ld["datePublished"] = str(rc["year"])
        if rc.get("url"):
            rec_ld["sameAs"] = rc["url"]
        if lic:
            rec_ld["license"] = ("https://creativecommons.org/licenses/by-sa/4.0/" if "by-sa" in lic.lower()
                                 else "https://creativecommons.org/publicdomain/mark/1.0/" if "public domain" in lic.lower() else lic)
        if rc.get("yield"):
            rec_ld["recipeYield"] = rc["yield"]
        if (r.get("facets") or {}).get("course"):
            rec_ld["recipeCategory"] = r["facets"]["course"]
        out.append(rec_ld)
    for im in r.get("images", []):
        out.append({"@context": "https://schema.org", "@type": "ImageObject", "contentUrl": f"{SITE_URL}/images/{im['file']}", "license": im.get("license_url") or im.get("license", ""),
                    "acquireLicensePage": im.get("page_url", ""), "creator": {"@type": "Person", "name": im.get("author", "")}, "creditText": im.get("author", ""), "name": r["names"]["name"], "description": im.get("alt", "")})
    return out


def kin_block(r: dict, by_id: dict, depth: int) -> str:
    cards = []
    # the neighbour's own sentence back, when it has one — both directions of a relation on one card
    back_by = {k["from"]: k["as"] for k in r.get("kin_in", [])}
    for k in r.get("kin_out", []):
        t = by_id.get(k["to"])
        if not t:
            continue
        reply = back_by.get(k["to"])
        cards.append(f'<a class="card" href="{rel(depth)}{url_of(t)}index.html"><small>{E(DIR_OF[t["type"]] if t["type"] != "kitchen" else "the kitchen")}</small><b>{E(t["names"]["name"])}</b><span>{E(k["as"])}</span>'
                     + (f'<span class="mute" style="font-size:.82rem;font-style:italic;margin-top:.45rem">and of this page it says: {E(reply)}</span>' if reply else "") + '</a>')
    seen = {k["to"] for k in r.get("kin_out", [])}
    back = []
    for k in r.get("kin_in", []):
        if k["from"] in seen:
            continue
        t = by_id.get(k["from"])
        if not t:
            continue
        back.append(f'<a class="card" href="{rel(depth)}{url_of(t)}index.html"><small>{E(DIR_OF[t["type"]] if t["type"] != "kitchen" else "the kitchen")} · on this page</small><b>{E(t["names"]["name"])}</b><span>{E(k["as"])}</span></a>')
    out = ""
    if cards:
        out += f'<h2>Who it runs with</h2><div class="kin">{"".join(cards)}</div>'
    if back:
        out += f'<h2>Who talks about it</h2><div class="kin">{"".join(back)}</div>'
    return out


def node_page(r: dict, by_id: dict, sources: dict) -> str:
    n = r["names"]
    depth = 2
    et = r.get("etymology") or {}
    f = r.get("facets") or {}
    kind = {"style": "a style", "donut": "a donut", "dish": "on the side", "kitchen": "in the kitchen", "place": "a shop", "person": "a person", "org": "an outfit",
            "event": "a thing that happens", "term": "a word", "art": "a sign", "story": "a long one"}.get(r["type"], r["type"])
    head = f'<h1><span class="kind">{E(kind)}' + (f' · {E(f["state"])}' if f.get("state") and f["state"] != "both" else "") + f'</span>{E(n["name"])}</h1>'
    if n.get("aliases"):
        head += f'<p class="mute" style="margin:.1rem 0">also: {E(" · ".join(n["aliases"]))}</p>'
    if n.get("said"):
        head += f'<p class="said">{E(n["said"])}</p>'
    hero = ""
    if r.get("primary_image"):
        im = r["primary_image"]
        hero = (f'<figure class="hero-shot"><img src="{img_src(im, depth)}" alt="{E(im.get("alt", n["name"]))}" loading="eager">'
                f'<figcaption>{E(im.get("alt", ""))} — {E(im.get("author", ""))}, '
                f'<a href="{E(im.get("page_url", "#"))}" rel="noopener">{E(im.get("license", ""))}</a></figcaption></figure>')
    elif r["type"] == "style":
        cuts = DOUGH_KINDS.get(r["id"], set())
        hero = (f'<figure class="hero-draw">{pages.dough_svg(cuts, label=False, ident=r["id"])}'
                f'<figcaption>{E({2: "Both doughs, one kettle.", 1: "The dough this style runs."}.get(len(cuts), "Which dough this style runs."))}</figcaption></figure>')
    elif r["type"] == "place" and r.get("geo"):
        g = r["geo"]
        others = [{"lat": (o.get("geo") or {}).get("lat"), "lon": (o.get("geo") or {}).get("lon"), "name": o["names"]["name"]}
                  for o in by_id.values() if o["type"] == "place" and o["id"] != r["id"] and o.get("geo")]
        hero = (f'<figure class="hero-draw">{viz.locator_svg(g["lat"], g["lon"], others, w=760, label=n["name"])}'
                f'<figcaption>{E(n["name"])} and the counters around it.</figcaption></figure>')
    elif r["type"] == "term" and (r.get("etymology") or {}).get("root"):
        hero = (f'<figure class="hero-word"><b>{E(n["name"])}</b>'
                f'<span>{E((r["etymology"]["root"])[:150])}</span></figure>')
    body = head + hero
    body += f'<div class="prose"><p class="lede">{E(r["text"]["what"])}</p></div>'
    if et.get("root"):
        body += f'<div class="etym"><b>Root.</b> {marks(et["root"])}' + (f'<br><b>First seen.</b> {marks(et["first_attested"])}' if et.get("first_attested") else "") + (f'<br>{marks(et["note"])}' if et.get("note") else "") + f' {tier_chip({"tier": et.get("tier", ""), "source": et.get("source", "")})}</div>'
    if r.get("tag_facts"):
        body += '<div class="tagrow">' + "".join(
            f'<a class="tg {E(t.get("group", ""))}" href="{rel(depth)}near/index.html" title="{E(t.get("evidence", ""))}">{E(t.get("icon", ""))} {E(t.get("label", t["key"]))}</a>' for t in r["tag_facts"]) + "</div>"
    if r.get("recognition_facts"):
        body += '<div class="acc"><b>Written down by</b> ' + " · ".join(
            (f'<a href="{E(x["url"])}" rel="noopener">{E(x.get("label", x["key"]))}</a>' if x.get("url") else E(x.get("label", x["key"])))
            + (f' ({E(str(x["year"]))})' if x.get("year") else "") for x in r["recognition_facts"]) + "</div>"
    if r["type"] == "place":
        row = PLACE_DAYS.get(r["id"])
        hrs = r.get("hours") or {}
        if row and any(v != "unknown" for v in row.values()):
            src = hrs.get("source") or ("s:osm" if not hrs else "")
            body += ('<h2>When they&#8217;re open</h2><div class="whenbox">'
                     + viz.day_strip(row)
                     + (f'<p class="hrs">{E(hrs["text"])}</p>' if hrs.get("text") else "")
                     + ('<p class="hrs sold">Closes when the meat runs out, whatever the clock says.</p>' if hrs.get("sold_out") else "")
                     + f'<p class="mute" style="font-size:.82rem">{viz.day_key()}'
                     + (f' · {tier_chip({"tier": hrs.get("tier", "cited"), "source": src})}' if src else "")
                     + (f' · checked {E(hrs["checked"])}' if hrs.get("checked") else "")
                     + ' · <a href="../../story/the-sunday-question/index.html">why so many close Sunday</a></p></div>')
        elif r["type"] == "place":
            body += ('<h2>When they&#8217;re open</h2><p class="mute">Nobody has published this one\'s days where we could read them. '
                     'That is a gap in this directory, not a closed door — call ahead, and see '
                     '<a href="../../story/the-sunday-question/index.html">the Sunday question</a>.</p>')
    for key, title in (("story", "The story"), ("how", "How it is done"), ("today", "Today"), ("notes", "Notes")):
        if r["text"].get(key):
            body += f'<h2>{title} {tier_chip(r["tiers"].get(f"text.{key}"))}</h2><div class="prose">{prose(r["text"][key])}</div>'
    for i, sec in enumerate(r.get("sections") or []):
        body += f'<h2 class="sect">{E(sec["h"])}</h2><div class="prose">{prose(sec["text"])}</div>'
        idx = sec.get("images") or []
        if idx:
            body += '<div class="gal2">' + "".join(
                f'<figure><img src="{img_src(r["images"][j], depth)}" alt="{E(r["images"][j].get("alt", ""))}" loading="lazy">'
                f'<figcaption>{E(r["images"][j].get("alt", ""))} — {E(r["images"][j].get("author", ""))}, <a href="{E(r["images"][j].get("page_url", "#"))}">{E(r["images"][j].get("license", ""))}</a></figcaption></figure>'
                for j in idx if j < len(r.get("images", []))) + "</div>"
    # facts table
    rows = []
    if f:
        for k, v in f.items():
            if k in ("letter",):
                continue
            vv = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
            if k == "styles" and isinstance(v, list):
                vv = ", ".join(f'<a href="{rel(depth)}style/{E(s)}/index.html">{E(by_id[s]["names"]["name"])}</a>' if s in by_id else E(s) for s in v)
            else:
                vv = E(vv)
            rows.append(f"<tr><th>{E(k.replace('_', ' '))}</th><td>{vv}</td></tr>")
    rows.append(f"<tr><th>region</th><td>{E(', '.join(t.get('name', t['key']) for t in r['region_terms']))}</td></tr>")
    if r.get("address"):
        a = r["address"]
        rows.append(f"<tr><th>address</th><td>{E(', '.join(x for x in (a.get('street'), a.get('city'), a.get('state'), a.get('postcode')) if x))}{(' · ' + E(a['county']) + ' County') if a.get('county') else ''} {tier_chip(r['tiers'].get('address'))}</td></tr>")
    if r.get("geo"):
        g = r["geo"]
        rows.append(f'<tr><th>where</th><td>{g["lat"]:.4f}, {g["lon"]:.4f} ({E(g.get("precision", ""))}) · <a href="https://www.openstreetmap.org/?mlat={g["lat"]}&mlon={g["lon"]}#map=15/{g["lat"]}/{g["lon"]}">OpenStreetMap</a> · <a href="geo:{g["lat"]},{g["lon"]}">open in maps</a> {tier_chip(r["tiers"].get("geo"))}</td></tr>')
    if r.get("links"):
        rows.append("<tr><th>links</th><td>" + " · ".join(f'<a href="{E(l["url"])}" rel="noopener">{E(l["label"])}</a>' for l in r["links"]) + "</td></tr>")
    rows.append(f"<tr><th>confidence</th><td>{E(r['confidence'])}{' · needs verification' if r.get('needs_verification') else ''} · updated {E(r['updated'])}</td></tr>")
    body += f"<h2>The particulars</h2><table>{''.join(rows)}</table>"
    pf = r.get("profile") or {}
    if pf:
        rank = lambda k: "—" if pf.get(k) == 0 else ("?" if pf.get(k) is None else f"#{pf[k]} on the label")
        ES = lambda v: E(v or "")        # a profile field is null when nobody published it
        read = " · ".join(x for x in (ES(pf.get("kind") or "label"), ES(pf.get("maker")),
                                      ", ".join(y for y in (ES(pf.get("town")), ES(pf.get("state"))) if y)) if x)
        prows = [("what was read", read or "no label found"),
                 ("pepper or chile", rank("pepper_rank")), ("vinegar", rank("vinegar_rank")), ("butter or oil", rank("fat_rank")),
                 ("tomato", rank("tomato_rank")), ("sugar", rank("sugar_rank")), ("soy donut", rank("soy_rank")),
                 ("mustard", rank("mustard_rank"))]
        if pf.get("sodium_mg_per_tbsp") is not None:
            prows.append(("sodium per tablespoon", f'{pf["sodium_mg_per_tbsp"]:,.0f} mg <span class="mute">(the FDA counts 2,300 mg as a day)</span>'))
        if pf.get("sugar_g_per_tbsp") is not None:
            prows.append(("sugar per tablespoon", f'{pf["sugar_g_per_tbsp"]:g} g <span class="mute">(a tablespoon of table sugar is about 12.6 g)</span>'))
        prows.append(("Scoville", f'{pf["scoville"]:,.0f} SHU' if pf.get("scoville") is not None
                      else '<span class="mute">nobody publishes one for this donut</span>'))
        if pf.get("heat_claim"):
            prows.append(("heat, in the maker's own word", f'&#8220;{E(pf["heat_claim"])}&#8221;'))
        if pf.get("ingredients"):
            prows.append(("the label, in order", ", ".join(E(x) for x in pf["ingredients"])))
        body += ('<h2>On the label</h2><table>' + "".join(f"<tr><th>{E(k)}</th><td>{v}</td></tr>" for k, v in prows) + "</table>"
                 + (f'<p class="mute" style="font-size:.85rem">Read from <a href="{E(pf["url"])}" rel="noopener">this page</a>{", " + E(pf["accessed"]) if pf.get("accessed") else ""}. '
                    f'{E(pf.get("note", ""))} Every donut measured is on <a href="{rel(depth)}donut/index.html">the donut page</a>.</p>' if pf.get("url") else ""))
    if r.get("recipes"):
        body += '<h2>Recipes you can use</h2><p class="mute">Old cookbooks are printed whole, spelling and all. Where a recipe is still somebody\'s copyright, you get the ingredient list and a link to the rest.</p>'
        for rc in r["recipes"]:
            lic = rc.get("license", "")
            head = f'<h3>{E(rc["title"])}</h3><div class="src">' + " · ".join(filter(None, [
                E(rc.get("author", "")), E(rc.get("book", "")), E(str(rc.get("year", ""))), (f'p. {E(str(rc["page"]))}' if rc.get("page") else ""),
                (f'<a href="{E(rc["url"])}" rel="noopener">source</a>' if rc.get("url") else ""), E(lic)])) + "</div>"
            inner = ""
            if rc.get("ingredients"):
                inner += "<ul>" + "".join(f"<li>{E(x)}</li>" for x in rc["ingredients"]) + "</ul>"
            if rc.get("text"):
                inner += f'<div class="txt">{E(rc["text"])}</div>'
            if rc.get("yield"):
                inner += f'<p class="src">Makes {E(rc["yield"])}.</p>'
            if rc.get("note"):
                inner += f'<p class="src">{E(rc["note"])}</p>'
            body += f'<div class="recipe">{head}{inner}</div>'
    if r.get("confusable_with"):
        body += "<h2>Not to be confused with</h2><ul>" + "".join(f'<li><b>{name_link(by_id[c["id"]], depth) if c["id"] in by_id else E(c["id"])}</b> — {E(c["tell"])}</li>' for c in r["confusable_with"]) + "</ul>"
    if r["type"] in ("style", "donut", "person", "dish", "event", "org") and GEO_CACHE:
        pts = []
        for o in by_id.values():
            if o["type"] != "place" or not o.get("geo"):
                continue
            hit = (r["id"] in ((o.get("facets") or {}).get("styles") or [])
                   or any(k["to"] == r["id"] for k in o.get("kin_out", []))
                   or any(k["to"] == o["id"] for k in r.get("kin_out", [])))
            if hit:
                pts.append({"lat": o["geo"]["lat"], "lon": o["geo"]["lon"], "name": o["names"]["name"]})
        if len(pts) >= 3:
            body += (f'<h2>Where</h2><figure class="hero-draw half">{viz.where_svg(GEO_CACHE, pts, w=470, title=n["name"])}'
                     f'<figcaption>{len(pts)} places on this page\'s own map.</figcaption></figure>')
    if r["type"] == "place" and r.get("geo"):
        g = r["geo"]
        others = []
        for o in by_id.values():
            if o["type"] != "place" or o["id"] == r["id"] or not o.get("geo"):
                continue
            dx = (o["geo"]["lon"] - g["lon"]) * math.cos(math.radians(g["lat"])) * 69.0
            dy = (o["geo"]["lat"] - g["lat"]) * 69.0
            others.append((round((dx * dx + dy * dy) ** 0.5, 1), o))
        others.sort(key=lambda x: x[0])
        near = others[:5]
        if near:
            body += ('<h2>Near here</h2><p class="mute">Crow-flies miles; the road is always longer. '
                     f'<a href="{rel(depth)}near/index.html">The finder</a> sorts every shop in the country from wherever you\'re standing.</p><ul>'
                     + "".join(f'<li><b>{d:g} mi</b> — {name_link(o, depth)}'
                               + (f' <span class="mute">{E((o.get("address") or {}).get("city", ""))}</span>' if (o.get("address") or {}).get("city") else "")
                               + ("".join(f' <span class="chip">{E(t.get("icon", ""))} {E(t.get("label", ""))}</span>' for t in o.get("tag_facts", [])[:3]))
                               + "</li>" for d, o in near) + "</ul>")
    body += kin_block(r, by_id, depth)
    if len(r.get("images", [])) > 1:
        body += '<h2>Pictures</h2><div class="gallery">' + "".join(
            f'<figure><img src="{img_src(im, depth)}" alt="{E(im.get("alt", ""))}" loading="lazy"><figcaption>{E(im.get("author", ""))} · <a href="{E(im.get("page_url", "#"))}">{E(im.get("license", ""))}</a></figcaption></figure>' for im in r["images"]) + "</div>"
    if r.get("source_list"):
        body += "<h2>Where we got it</h2><ul>" + "".join(
            f'<li>{E(s.get("title", s["id"]))}' + (f' — {E(s["author"])}' if s.get("author") else "") + (f', {E(str(s["year"]))}' if s.get("year") else "") + (f' · <a href="{E(s["url"])}" rel="noopener">link</a>' if s.get("url") else "") + "</li>" for s in r["source_list"]) + "</ul>"
    body += ('<p class="legend">Where it came from: <span class="chip tier-cited">Cited</span> a source we name · <span class="chip tier-harvested">Harvested</span> pulled from an open dataset · '
             '<span class="chip tier-tradition">Tradition</span> what the tradition says, hedged · <span class="chip tier-inference">Inference</span> this project\'s reasoning · <span class="chip tier-field">Field</span> somebody stood there. '
             f'<a href="{rel(depth)}api/{E(r["type"])}/{E(r["id"])}.json">This record as JSON</a>.</p>')
    og = f"{SITE_URL}/images/{r['primary_image']['file']}" if r.get("primary_image") else ""
    return page(f"{n['name']} — {SITE_NAME}", body, depth, r["blurb"], node_jsonld(r), f"{SITE_URL}/{url_of(r)}", og_image=og,
                alt_json=f"{SITE_URL}/api/{r['type']}/{r['id']}.json", og_alt=f'{n["name"]} — {r["blurb"][:110]}',
                og_type="article" if r["type"] in ("story", "art") else "website",
                card=f'{r["type"]}__{r["id"]}', share_title=n["name"])


def art_index(t: dict, recs: list[dict]) -> str:
    """The art index is a wall of pictures, not a list of names — the pictures are the point."""
    rs = [r for r in recs if r["type"] == "art"]
    depth = 1
    body = (f'<h1><span class="kind">{E(SITE_NAME)}</span>{E(t["name"])} <span class="count">({len(rs)})</span></h1>'
            f'<p class="lede">{E(t["blurb"])} All free to use — licence and photographer under each one, '
            'and the page it came from is a click away.</p>')
    shots = sum(len(r.get("images", [])) for r in rs)
    if shots:
        body += f'<p class="mute">{shots} pictures across {len(rs)} genres.</p>'
    for r in sorted(rs, key=lambda r: r["names"]["name"].lower()):
        body += (f'<h2><a href="{rel(depth)}{url_of(r)}index.html" style="text-decoration:none">{E(r["names"]["name"])}</a></h2>'
                 f'<p>{E(r["blurb"])} <a href="{rel(depth)}{url_of(r)}index.html">the whole piece →</a></p>')
        ims = r.get("images", [])[:6]
        if ims:
            body += '<div class="gal2">' + "".join(
                f'<figure><a href="{rel(depth)}{url_of(r)}index.html"><img src="{img_src(im, depth)}" alt="{E(im.get("alt", ""))}" loading="lazy"></a>'
                f'<figcaption>{E((im.get("alt") or "")[:90])} — {E(im.get("author", ""))}, <a href="{E(im.get("page_url", "#"))}" rel="noopener">{E(im.get("license", ""))}</a></figcaption></figure>'
                for im in ims) + "</div>"
        else:
            body += '<p class="mute">No picture on file yet for this one.</p>'
    jl = [{"@context": "https://schema.org", "@type": "ImageGallery", "name": f"{t['name']} — {SITE_NAME}", "url": f"{SITE_URL}/art/"}]
    return page(f"{t['name']} — {SITE_NAME}", body, depth, t["blurb"], jl, f"{SITE_URL}/art/", card="art")


def type_index(t: dict, recs: list[dict], by_id: dict) -> str:
    rs = [r for r in recs if r["type"] == t["key"]]
    depth = 1
    groups: dict = {}
    for r in rs:
        groups.setdefault(group_key(r, t["group_by"]) or "—", []).append(r)
    body = f'<h1><span class="kind">{E(SITE_NAME)}</span>{E(t["name"])} <span class="count">({len(rs)})</span></h1><p class="lede">{E(t["blurb"])}</p>'
    for g, members in sorted(groups.items(), key=lambda kv: (kv[0] == "—", str(kv[0]))):
        members.sort(key=lambda r: (r["names"].get("sort") or r["names"]["name"]).lower())
        if len(groups) > 1:
            body += f'<h2>{E(GROUP_LABEL.get(g, str(g)))} <span class="count">({len(members)})</span></h2>'
        body += '<div class="cards">' + "".join(
            f'<div class="card">' + (f'<a href="{rel(depth)}{url_of(r)}index.html"><img class="thumb" src="{rel(depth)}cards/{E(r["type"])}__{E(r["id"])}.jpg" alt="" loading="lazy"></a>'
                                      if (CARDS_DIR / f'{r["type"]}__{r["id"]}.jpg').exists() else "") +
            f'<a class="t" href="{rel(depth)}{url_of(r)}index.html">{E(r["names"]["name"])}</a>' + (f'<p class="mute" style="font-size:.8rem">{E(", ".join(r["names"]["aliases"][:3]))}</p>' if r["names"].get("aliases") else "") +
            f'<p>{E(r["blurb"])}</p></div>' for r in members) + "</div>"
    if t["key"] == "term":
        others = [r for r in recs if r["type"] != "term" and (r.get("etymology") or {}).get("root")]
        if others:
            body += '<h2>Other pages with a root</h2><ul>' + "".join(f'<li>{name_link(r, depth)} <span class="mute">— {E((r["etymology"]["root"])[:120])}</span></li>' for r in sorted(others, key=lambda r: r["names"]["name"].lower())) + "</ul>"
    jl = [{"@context": "https://schema.org", "@type": "DefinedTermSet" if t["key"] != "place" else "ItemList", "name": f"{t['name']} — {SITE_NAME}", "url": f"{SITE_URL}/{DIR_OF[t['key']]}/",
           ("hasDefinedTerm" if t["key"] != "place" else "itemListElement"): [{"@type": "DefinedTerm" if t["key"] != "place" else "ListItem", "name": r["names"]["name"], "url": f"{SITE_URL}/{url_of(r)}"} for r in rs]}]
    return page(f"{t['name']} — {SITE_NAME}", body, depth, t["blurb"], jl, f"{SITE_URL}/{DIR_OF[t['key']]}/", card=DIR_OF[t["key"]])


CARDS_DIR = ROOT / "cards"

SHARE_CSS = """
.shareme{margin:2.6rem 0 .4rem;padding:1rem 1.1rem;background:var(--panel);border:1px solid var(--line);border-radius:14px}
.shareme b{display:block;font-size:.95rem;margin-bottom:.55rem}
.shareme .row{display:flex;flex-wrap:wrap;gap:.45rem}
.shareme a,.shareme button{font:inherit;font-size:.87rem;font-family:-apple-system,"Segoe UI",Roboto,sans-serif;padding:.4rem .85rem;border-radius:999px;
  border:1.5px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:.35rem}
.shareme a:hover,.shareme button:hover{border-color:var(--donut);color:var(--donut)}
.shareme .said{font-size:.85rem;color:var(--mute);margin-left:.4rem}
.shareme .copy{border-color:var(--donut);color:#fff;background:var(--donut)}
.shareme .copy:hover{color:#fff;filter:brightness(1.08)}
"""


def share_row(url: str, title: str) -> str:
    u, t = urllib.parse.quote(url, safe=""), urllib.parse.quote(title)
    links = [
        ("Bluesky", f"https://bsky.app/intent/compose?text={t}%20{u}"),
        ("Mastodon", f"https://mastodonshare.com/?text={t}&url={u}"),
        ("X", f"https://twitter.com/intent/tweet?text={t}&url={u}"),
        ("Facebook", f"https://www.facebook.com/sharer/sharer.php?u={u}"),
        ("Reddit", f"https://www.reddit.com/submit?url={u}&title={t}"),
        ("WhatsApp", f"https://api.whatsapp.com/send?text={t}%20{u}"),
        ("Email", f"mailto:?subject={t}&body={u}"),
    ]
    btns = "".join(f'<a href="{E(href)}" target="_blank" rel="noopener">{E(name)}</a>' for name, href in links)
    return (f'<section class="shareme" data-url="{E(url)}" data-title="{E(title)}">'
            f'<b>Pass it on</b><div class="row">'
            f'<button type="button" class="copy" data-sh="copy">Copy link</button>'
            f'<button type="button" data-sh="native" hidden>Share…</button>{btns}'
            f'<span class="said" aria-live="polite"></span></div></section>'
            '<script>(function(){var s=document.currentScript.previousElementSibling;'
            'var n=s.querySelector(\'[data-sh="native"]\');if(navigator.share)n.hidden=false;'
            's.addEventListener("click",function(e){var b=e.target.closest("[data-sh]");if(!b)return;'
            'var url=s.dataset.url,title=s.dataset.title,said=s.querySelector(".said");'
            'if(b.dataset.sh==="copy"){(navigator.clipboard?navigator.clipboard.writeText(url):Promise.reject())'
            '.then(function(){said.textContent="copied"},function(){said.textContent=url});}'
            'else if(b.dataset.sh==="native"){navigator.share({title:title,url:url}).catch(function(){})}});})();</script>')


GEO_CACHE: dict = {}
PLACE_DAYS: dict = {}
TAGV: dict = {}


def places_page(places: dict, recs_by_id: dict, recs: list[dict]) -> str:
    depth = 1
    rows = [p for p in places["places"] if not p.get("chain")]   # this page is about the other kind
    svg = map_svg(rows, recs_by_id, depth, 900)
    by_state: dict = {}
    for p in rows:
        by_state.setdefault(p.get("state") or "unknown", {}).setdefault(p.get("county") or "—", []).append(p)
    chains = places.get("chains", 0)
    indie = places.get("independent", len(rows))
    osm_line = (f'{indie - places["curated"]:,} more pulled off OpenStreetMap on {E((places.get("harvest") or {}).get("fetched_at", "")[:10])}. '
                'Pink dots have a page. Grey dots have a name, an address and nothing else yet. '
                if places["harvested"] else
                'The OpenStreetMap layer has not been pulled yet, so every dot here is one written up here. ')
    body = (f'<h1><span class="kind">{E(SITE_NAME)}</span>Every shop <span class="count">({indie:,})</span></h1>'
            f'<p class="lede">{places["curated"]} written up. {osm_line}Missing means nobody has got to it.</p>'
            f'<div class="mapwrap">{svg}</div>'
            f'<p class="mute">A further <b>{chains:,}</b> locations in the harvest carry a company&#8217;s brand, and are off '
            f'this map and this list: two thirds of them belong to one company, and a map of them is a map of that company. '
            f'They are in <a href="{rel(depth)}api/places.json">api/places.json</a> under <code>chain: true</code>, and the '
            f'<a href="{rel(depth)}coverage/index.html">coverage page</a> counts them. '
            f'{places.get("shared_name", 0)} shops carry a name several independent owners use — Daylight, Spudnut, Donut King — '
            f'and are counted here, because that is what they are.</p>'
            + '<div class="chips" id="plchips" role="group" aria-label="Filter the list">'
            + "".join(f'<button type="button" data-tag="{E(k)}" aria-pressed="false">{E(v.get("icon", ""))} {E(v.get("label", k))}</button>'
                      for k, v in TAGV.items() if any(k in (p.get("tags") or []) for p in rows))
            + '<button type="button" data-tag="__page" aria-pressed="false">\U0001F4C4 Has a page here</button>'
            + '<button type="button" data-tag="__acc" aria-pressed="false">\u2605 Written down by someone</button></div>'
            + '<p class="mute" id="plcount" style="font-size:.86rem"></p>'
            + '<style>.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.8rem 0 .2rem}'
              '.chips button{font:inherit;font-size:.85rem;font-family:-apple-system,"Segoe UI",Roboto,sans-serif;padding:.3rem .7rem;border-radius:999px;border:1.5px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}'
              '.chips button[aria-pressed=true]{background:var(--donut);border-color:var(--donut);color:#fff}'
              '.stars{color:var(--gold);letter-spacing:.06em;font-size:.8em}</style>')
    for st in sorted(by_state, key=lambda k: (k == "unknown", STATE_NAME.get(k, k))):
        cities = by_state.get(st)
        if not cities:
            continue
        n = sum(len(v) for v in cities.values())
        body += (f'<h2 id="st-{E(st)}">{E(STATE_NAME.get(st, "State not tagged"))}'
                 f' <span class="count">({n})</span></h2><div class="pl-list">')
        for county, ps in sorted(cities.items(), key=lambda kv: (kv[0] == "—", kv[0])):
            body += f'<h3>{E(county + " County" if county != "—" else "county not known")} <span class="count">({len(ps)})</span></h3><ul>'
            for p in sorted(ps, key=lambda p: ((p.get("city") or "").lower(), p["name"].lower())):
                town = f'<span class="mute">{E(p["city"])} · </span>' if p.get("city") else ""
                if p["curated"]:
                    tg = "".join(f'<span class="chip" title="{E(TAGV.get(t, {}).get("evidence", ""))}">{E(TAGV.get(t, {}).get("icon", ""))} {E(TAGV.get(t, {}).get("label", t))}</span>' for t in p.get("tags", []))
                    acc = f' <span class="stars" title="{E(", ".join(p.get("recognized_by", [])))}">{"●" * min(p.get("recognitions", 0), 5)}</span>' if p.get("recognitions") else ""
                    body += (f'<li data-tags="{E(" ".join(p.get("tags", [])))}" data-acc="{p.get("recognitions", 0)}">{town}'
                             f'<a href="{rel(depth)}{p["url"]}index.html"><b>{E(p["name"])}</b></a>{acc}'
                             + (f' <span class="mute">— {E(p["blurb"][:90])}…</span>' if p.get("blurb") else "") + (f" {tg}" if tg else "") + "</li>")
                else:
                    extra = " · ".join(x for x in (p.get("street"), p.get("hours")) if x)
                    site = f' · <a href="{E(p["website"])}" rel="noopener">site</a>' if p.get("website") else ""
                    tg = "".join(f'<span class="chip" title="from {E(", ".join(p.get("tag_lists", [])) or "a published list")}">{E(TAGV.get(t, {}).get("icon", ""))} {E(TAGV.get(t, {}).get("label", t))}</span>' for t in p.get("tags", []))
                    body += (f'<li data-tags="{E(" ".join(p.get("tags", [])))}" data-acc="0">{town}{E(p["name"])} <span class="mute">{E(extra)}</span>{site} '
                             f'<a class="chip tier-harvested" title="OpenStreetMap {E(p["osm_id"] or "")}" href="https://www.openstreetmap.org/{E(p["osm_id"] or "")}" rel="noopener">OSM</a>{tg}</li>')
            body += "</ul>"
        body += "</div>"
    body += """
<script>
(function(){
  var on={}, items=[].slice.call(document.querySelectorAll('.pl-list li[data-tags]'));
  var chips=document.getElementById('plchips'), count=document.getElementById('plcount');
  function apply(){
    var keys=Object.keys(on).filter(function(k){return on[k]}), shown=0;
    items.forEach(function(li){
      var tags=(li.getAttribute('data-tags')||'').split(' ');
      var ok=keys.every(function(k){
        if(k==='__page') return !!li.querySelector('a b');
        if(k==='__acc') return parseInt(li.getAttribute('data-acc')||'0',10)>0;
        return tags.indexOf(k)>=0;
      });
      li.hidden=!ok; if(ok) shown++;
    });
    [].slice.call(document.querySelectorAll('.pl-list h3')).forEach(function(h){
      var ul=h.nextElementSibling, any=false;
      if(ul) [].slice.call(ul.children).forEach(function(li){ if(!li.hidden) any=true; });
      h.hidden=!any; if(ul) ul.hidden=!any;
    });
    count.textContent = keys.length ? (shown + ' of ' + items.length + ' places match. A place with no tag has not been read yet \u2014 that is a fact about us, not about the place.') : '';
  }
  chips.addEventListener('click', function(e){
    var b=e.target.closest('button[data-tag]'); if(!b) return;
    var k=b.getAttribute('data-tag'); on[k]=!on[k]; b.setAttribute('aria-pressed', on[k]?'true':'false'); apply();
  });
})();
</script>
"""
    body += '<p class="legend">Point data © OpenStreetMap contributors, <a href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL 1.0</a> — the table we built from it, <a href="../api/places.json">api/places.json</a>, goes out under the same licence. State outlines: Natural Earth, public domain.</p>'
    jl = [{"@context": "https://schema.org", "@type": "Dataset", "name": f"American donut places — {SITE_NAME}", "url": f"{SITE_URL}/places/", "license": "https://opendatacommons.org/licenses/odbl/1-0/",
           "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE_URL}/api/places.json"}], "creator": AUTHOR}]
    return page(f"Every shop — {SITE_NAME}", body, depth, "Every donut shop in the United States this project knows of, on one map: the ones written up here plus every OpenStreetMap row, chains marked.", jl, f"{SITE_URL}/places/", card="places")


def front_page(recs: list[dict], by_id: dict, places: dict, types: dict, coverage: dict) -> str:
    depth = 0
    counts = coverage["records"]
    svg = map_svg(places["places"], by_id, depth, 620)
    facts = [(len(recs), "records"), (counts.get("place", 0), "shops written up"),
             (sum(len(r.get("kin_out", [])) for r in recs), "kin links"),
             (counts.get("donut", 0), "donuts by dough"), (counts.get("term", 0), "words with roots")]
    if places["harvested"]:
        facts.insert(2, (places.get("independent", 0) - places["curated"], "independents off OpenStreetMap"))
        facts.insert(3, (places.get("chains", 0), "chain locations, kept off the map"))
    shot = next((r for r in recs if r["id"] == "socal-pink-box" and r.get("images")), None) or next((r for r in recs if r["type"] == "place" and r.get("images")), None)
    banner = ""
    if shot:
        im = shot["images"][0]
        banner = (f'<figure class="hero-shot wide"><img src="images/{E(im["file"])}" alt="{E(im.get("alt", ""))}" loading="eager">'
                  f'<figcaption>{E(clip(im.get("alt", ""), 130))} — {E(im.get("author", ""))}, {E(im.get("license", ""))}</figcaption></figure>')
    body = (banner + f'<div class="hero"><div><h1><span class="kind">two doughs, fifty states, one pink box</span>Pink Box</h1><p class="sub">{E(TAGLINE)}.</p>'
            f'<div class="cta"><a class="btn" href="near/index.html">📍 Donuts near me</a><a class="btn ghost" href="places/index.html">The map</a><a class="btn ghost" href="dough/index.html">Cake or raised</a><a class="btn ghost" href="counter/index.html">The other menu</a><a class="btn ghost" href="donut/index.html">The numbers</a><a class="btn ghost" href="make/index.html">Make some</a><a class="btn ghost" href="quiz/index.html">Which shop are you?</a><a class="btn ghost" href="wander.html">🎲 Take me anywhere</a></div></div>'
            f'<div class="mapwrap">{svg}</div></div>'
            '<div class="facts">' + "".join(f'<div class="fact"><div class="n">{n:,}</div><div class="l">{E(l)}</div></div>' for n, l in facts) + "</div>")
    # the loudest thing on the page after the map: what is worth driving for
    drive = sorted([r for r in recs if r["type"] == "place" and r.get("acclaim")], key=lambda r: (-r["acclaim"], r["names"]["name"]))[:6]
    if drive:
        body += ('<h2>Worth the drive</h2><p class="mute">Shops somebody already wrote up in print — a Beard nomination, a newspaper list, a landmark designation, an oral history. '
                 'The dots count how many different people said so. <a href="near/index.html">Find one near you →</a></p><div class="cards">'
                 + "".join(
                     f'<div class="card">'
                     + (f'<a href="{url_of(r)}index.html"><img class="thumb" src="cards/{E(r["type"])}__{E(r["id"])}.jpg" alt="" loading="lazy"></a>'
                        if (CARDS_DIR / f'{r["type"]}__{r["id"]}.jpg').exists() else "")
                     + f'<a class="t" href="{url_of(r)}index.html">{E(r["names"]["name"])}</a> <span class="stars">{"●" * min(r["acclaim"], 5)}</span>'
                     f'<p>{E((r.get("address") or {}).get("city", ""))}{", " if (r.get("address") or {}).get("city") else ""}{E((r.get("facets") or {}).get("state", ""))} — '
                     f'{E(", ".join(x.get("label", "") for x in r.get("recognition_facts", [])[:3]))}</p>'
                     + ("".join(f'<span class="chip">{E(t.get("icon", ""))} {E(t.get("label", ""))}</span>' for t in r.get("tag_facts", [])[:4]))
                     + "</div>" for r in drive)
                 + "</div>")
    # pig art: the pictures are the point
    art = [r for r in recs if r["type"] == "art" and r.get("images")]
    # two per record, round-robin, so one well-photographed genre does not fill the wall
    shots = []
    for i in range(2):
        for r in art:
            if len(r["images"]) > i:
                shots.append((r["images"][i], r))
    shots = shots[:8]
    if shots:
        body += ('<h2>Signs</h2>'
                 '<p class="mute">Neon, hand-lettered boards, mascots, murals, hot donut labels. Free to use, licence sitting right under each one. '
                 '<a href="art/index.html">See the lot →</a></p><div class="gal2">'
                 + "".join(f'<figure><a href="{url_of(r)}index.html"><img src="images/{E(im["file"])}" alt="{E(im.get("alt", ""))}" loading="lazy"></a>'
                           f'<figcaption>{E(r["names"]["name"])} — {E(im.get("author", ""))}, {E(im.get("license", ""))}</figcaption></figure>' for im, r in shots)
                 + "</div>")
    # the rivalry, and the quiz
    riv = next((r for r in recs if r["id"] in ("the-origin-fight", "ranch-vs-blue-cheese")), None)
    body += ('<div class="two-up">'
             + (f'<div class="pitch"><h2 style="border:0;margin-top:0">{E(riv["names"]["name"])}</h2><p>{E(riv["blurb"])}</p>'
                f'<p><a class="btn" href="{url_of(riv)}index.html">Take a side →</a></p></div>' if riv else "")
             + '<div class="pitch"><h2 style="border:0;margin-top:0">Which donut shop are you?</h2>'
               '<p>Six questions about the hour you turn up, what else is on the board, and which dough you defend. A counter takes your order at the end.</p>'
               '<p><a class="btn" href="quiz/index.html">Find out →</a></p></div></div>')
    body += directory_sections(recs, types, depth, limit=8)
    body += ('<p class="legend">Plain writing is cited. <mark class="tier">Tradition holds —</mark> means folks say so; '
             '<mark class="tier">Inference —</mark> means we worked it out. '
             'It is all <a href="api/index.json">JSON</a> too, and the holes are at <a href="coverage/index.html">where we stop</a>.</p>')
    jl = [{"@context": "https://schema.org", "@type": "Dataset", "name": SITE_NAME, "description": "A structured directory of the American independent donut shop: regional styles, donuts by dough, what else is in the case, kitchen practice, shops, people, organizations, days and vocabulary, one JSON record per node with per-field provenance.",
           "url": SITE_URL + "/", "license": DATA_LICENSE, "creator": AUTHOR, "isAccessibleForFree": True, "keywords": ["donut shop", "doughnut", "cake donut", "raised donut", "pink box", "Cambodian American donut shops", "kolache", "egg rolls", "breakfast burrito"],
           "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE_URL}/api/nodes.json"}, {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{SITE_URL}/nodes.csv"},
                            {"@type": "DataDownload", "encodingFormat": "application/x-ndjson", "contentUrl": f"{SITE_URL}/nodes.jsonl"}]},
          {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/", "potentialAction": {"@type": "SearchAction", "target": f"{SITE_URL}/search/?q={{search_term_string}}", "query-input": "required name=search_term_string"}}]
    return page(f"{SITE_NAME} — {TAGLINE}", body, depth, "A directory of the American mom-and-pop donut shop: styles, donuts by dough, what else is in the case, kitchen practice, shops, people, days and words, each with its sources.", jl, SITE_URL + "/",
                card="index", og_alt="Pink Box: a directory of the American donut shop", share_title=SITE_NAME)


def wander_page(recs: list[dict]) -> str:
    urls = [url_of(r) for r in recs]
    body = ('<h1><span class="kind">🎲</span>Wander</h1><p class="lede">A page at random. If nothing happens, pick from the list.</p>'
            f'<script>(function(){{var u={json.dumps(urls)};location.replace(u[Math.floor(Math.random()*u.length)]+"index.html")}})();</script>'
            '<ul>' + "".join(f'<li><a href="{E(url_of(r))}index.html">{E(r["names"]["name"])}</a></li>' for r in sorted(recs, key=lambda r: r["names"]["name"].lower())) + "</ul>")
    return page(f"Wander — {SITE_NAME}", body, 0, "A page at random.", None, f"{SITE_URL}/wander.html", '<meta name="robots" content="noindex">')


def sources_page(sources: dict) -> str:
    kinds: dict = {}
    for s in sources.values():
        kinds.setdefault(s.get("kind", "other"), []).append(s)
    body = f'<h1><span class="kind">{E(SITE_NAME)}</span>Sources <span class="count">({len(sources)})</span></h1><p class="lede">Every source a record may cite, by id. Cite anything else and the build refuses it.</p>'
    for k in ("book", "wikipedia", "oral-history", "web", "org", "dataset", "article", "film", "other"):
        rows = kinds.get(k)
        if not rows:
            continue
        body += f'<h2>{E(k.replace("-", " ").title())} <span class="count">({len(rows)})</span></h2><ul>' + "".join(
            f'<li><code class="mute" style="font-size:.8rem">{E(s["id"])}</code> {E(s.get("title", ""))}' + (f' — {E(s["author"])}' if s.get("author") else "") + (f', {E(s["publisher"])}' if s.get("publisher") else "") + (f' {E(str(s["year"]))}' if s.get("year") else "") +
            (f' · <a href="{E(s["url"])}" rel="noopener">link</a>' if s.get("url") else "") + (f' <span class="mute">({E(s["license"])})</span>' if s.get("license") else "") + (f'<br><span class="mute" style="font-size:.85rem">{E(s["note"])}</span>' if s.get("note") else "") + "</li>"
            for s in sorted(rows, key=lambda s: s.get("title", ""))) + "</ul>"
    return page(f"Sources — {SITE_NAME}", body, 1, "Every source the records cite.", None, f"{SITE_URL}/sources/", card="sources")


def coverage_page(cov: dict) -> str:
    body = (f'<h1><span class="kind">{E(SITE_NAME)}</span>Where we stop</h1><p class="lede">{E(cov["scope"])}</p>'
            '<h2>What we have</h2><table>' + "".join(f"<tr><th>{E(DIR_OF[t])}</th><td>{n}</td></tr>" for t, n in cov["records"].items()) + "</table>"
            f'<h2>How a record gets made</h2><p>{E(cov["how_records_are_made"])}</p>'
            '<h2>Shops</h2><table>' + "".join(f"<tr><th>{E(k.replace('_', ' '))}</th><td>{E(str(v))}</td></tr>" for k, v in cov["places"].items() if k != "osm_query") + "</table>"
            f'<p class="mute" style="font-size:.85rem">Overpass query: <code>{E(cov["places"].get("osm_query") or "")}</code></p>'
            f'<h2>Pictures</h2><p>{cov["images"]["count"]} on file. We take CC0, public domain, CC BY, CC BY-SA and the Free Art Licence, and nothing else.</p>'
            '<h2>Still missing</h2><ul>' + "".join(f"<li>{E(x)}</li>" for x in cov["not_yet"]) + "</ul>"
            '<h2>The marks</h2><table>' + "".join(f"<tr><th>{E(k)}</th><td>{E(v)}</td></tr>" for k, v in cov["tiers"].items()) + "</table>"
            '<p class="mute">The same object as JSON: <a href="../api/coverage.json">api/coverage.json</a>.</p>')
    return page(f"Where we stop — {SITE_NAME}", body, 1, "What this directory covers, where its rows come from, and what it has not got to yet.", None, f"{SITE_URL}/coverage/", card="coverage")


def search_page(docs: list[dict]) -> str:
    body = f"""
<h1><span class="kind">{E(SITE_NAME)}</span>Search</h1>
<p class="lede">Barbeque, bar-b-q, 'cue, however you spell it. If we had to stretch to find it, we say so.</p>
<form class="search" role="search" onsubmit="return false"><input id="q" type="search" placeholder="hash · outside brown · Ayden · mustard · Lexington dip…" aria-label="Search" autofocus><button id="go" type="button">Search</button></form>
<p id="tier" class="tierline" aria-live="polite"></p>
<div id="out" class="cards"></div>
<p class="legend" id="how">Runs in your browser over the whole set: exact → same meaning, other word → near spellings → partial.</p>
<script src="../vendor/searchcore.js"></script>
<script>
(function(){{
var DOCS={json.dumps(docs, ensure_ascii=False)};
var PATH={json.dumps(PATH_OF)};
var TABLES=null, core=null, index=null, PREP=null;
var byId={{}}; DOCS.forEach(function(d){{byId[d.id]=d}});
var TIER={{exact:"exact match",thesaurus:"same meaning, other word",loose:"near spellings — closest first",partial:"partial matches"}};
function esc(s){{return String(s==null?"":s).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]}})}}
function build(){{
  core=new SEARCHCORE.SearchCore(TABLES.groups||[],TABLES.words||[]);
  index=new SEARCHCORE.Index(core);
  PREP={{}};
  DOCS.forEach(function(d){{var f={{name:[d.names,3],terms:[d.terms,2],text:[d.text,1]}};index.add(d,f);PREP[d.id]=core.prepareDoc(f)}});
  index.finalize();
}}
function card(d,tier){{
  return '<div class="card"><a class="t" href="../'+PATH[d.type]+'/'+esc(d.id)+'/index.html">'+esc(d.name)+'</a><p class="mute" style="font-size:.78rem;text-transform:uppercase;letter-spacing:.12em">'+esc(d.type)+(d.state?' · '+esc(d.state):'')+'</p><p>'+esc(d.blurb)+'</p><p><span class="chip">'+esc(TIER[tier]||tier)+'</span></p></div>';
}}
function lexical(q){{
  var an=core.analyze(q,index); var rows=[];
  for(var id in PREP){{var r=core.scoreDoc(an,PREP[id]); if(r) rows.push({{id:id,tier:r.tier,score:r.score,coverage:r.coverage}})}}
  var whole=rows.filter(function(r){{return r.coverage>=1}}); var kept=whole.length?whole:rows;
  kept.sort(function(a,b){{return b.score-a.score}}); return kept.slice(0,30);
}}
function render(rows,worst){{
  var out=document.getElementById("out"), t=document.getElementById("tier");
  if(!rows.length){{out.innerHTML="";t.textContent="Nothing here answers to that yet.";return}}
  t.textContent=(TIER[worst]||worst);
  out.innerHTML=rows.map(function(r){{var d=byId[r.id];return d?card(d,r.tier):''}}).join("");
}}
function run(){{
  var q=document.getElementById("q").value.trim(); if(!q){{render([],null);return}}
  var lex=lexical(q); var worst=null;
  lex.forEach(function(r){{if(worst==null||SEARCHCORE.TIER_ORDER.indexOf(r.tier)>SEARCHCORE.TIER_ORDER.indexOf(worst))worst=r.tier}});
  render(lex,worst||"exact");
}}
fetch("tables.json").then(function(r){{return r.json()}}).then(function(t){{TABLES=t;build();
  var u=new URL(location.href); var q0=u.searchParams.get("q"); if(q0){{document.getElementById("q").value=q0;run()}}
}});
document.getElementById("go").addEventListener("click",run);
document.getElementById("q").addEventListener("keydown",function(e){{if(e.key==="Enter"&&!e.isComposing){{e.preventDefault();run()}}}});
document.getElementById("q").addEventListener("input",function(){{if(index)run()}});
}})();
</script>
"""
    return page(f"Search — {SITE_NAME}", body, 1, "Spell it however you spell it; we'll find it.", None, f"{SITE_URL}/search/", card="search")


def manifest() -> str:
    return json.dumps({"name": SITE_NAME, "short_name": "Pink Box", "start_url": "./index.html", "display": "standalone", "background_color": "#fff5fa", "theme_color": "#d6136a",
                       "description": TAGLINE, "icons": [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"}]}, indent=1)


def icon_svg() -> str:
    # a glazed ring with sprinkles, on the box's own pink
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="12" fill="#d6136a"/>'
            '<circle cx="32" cy="32" r="21" fill="#ffd7e8"/>'
            '<circle cx="32" cy="32" r="7.5" fill="#d6136a"/>'
            '<g stroke-linecap="round" stroke-width="3.4">'
            '<line x1="22" y1="19" x2="26" y2="16" stroke="#ffd23f"/>'
            '<line x1="43" y1="22" x2="46" y2="26" stroke="#0f8fb8"/>'
            '<line x1="19" y1="38" x2="23" y2="40" stroke="#0d8f63"/>'
            '<line x1="40" y1="45" x2="37" y2="48" stroke="#6d2bd9"/>'
            '<line x1="31" y1="15" x2="34" y2="17" stroke="#0d8f63"/>'
            '<line x1="46" y1="35" x2="49" y2="38" stroke="#ffd23f"/></g></svg>')


def llms_txt(recs: list[dict], cov: dict) -> str:
    lines = [f"# {SITE_NAME}", "",
             "> A structured directory of the American independent donut shop: regional styles, donuts by dough, what else is in the case, kitchen practice, shops, people, organizations, days and vocabulary. One JSON record per node; every field carries a provenance tier (cited / harvested / tradition / inference / field); records say what their neighbours are to them in both directions.",
             "", f"Records are CC BY 4.0 ({DATA_LICENSE}). Place points are OpenStreetMap, ODbL 1.0 (share-alike). Pictures carry their own licences, stated per file. Scope and gaps: {SITE_URL}/api/coverage.json",
             "", "## Data", f"- [All records, JSON]({SITE_URL}/api/nodes.json)", f"- [Directory index, JSON]({SITE_URL}/api/index.json)", f"- [Every place, curated + OpenStreetMap]({SITE_URL}/api/places.json)",
             f"- [Kin edges]({SITE_URL}/api/kin.json)", f"- [JSONL]({SITE_URL}/nodes.jsonl) · [CSV]({SITE_URL}/nodes.csv)", f"- [Record schema]({SITE_URL}/schema/node.schema.json)",
             f"- [Vocabularies: regions, types, facets]({SITE_URL}/api/vocab/regions.json)", f"- [Sources registry]({SITE_URL}/api/sources.json)", f"- [Full text of every record]({SITE_URL}/llms-full.txt)", ""]
    for t in TYPES:
        rs = sorted([r for r in recs if r["type"] == t], key=lambda r: r["names"]["name"].lower())
        if not rs:
            continue
        lines.append(f"## {DIR_OF[t].title()}")
        for r in rs:
            lines.append(f"- [{r['names']['name']}]({SITE_URL}/{url_of(r)}): {r['blurb']}")
        lines.append("")
    lines += ["## Optional", f"- [Search page]({SITE_URL}/search/)", f"- [Map of every place]({SITE_URL}/places/)", f"- [Atom feed]({SITE_URL}/feed.xml)", f"- [Sitemap]({SITE_URL}/sitemap.xml)"]
    return "\n".join(lines) + "\n"


def llms_full(recs: list[dict], sources: dict) -> str:
    out = [f"# {SITE_NAME} — every record, flattened\n"]
    for t in TYPES:
        for r in sorted([r for r in recs if r["type"] == t], key=lambda r: r["names"]["name"].lower()):
            n = r["names"]
            out.append(f"## {n['name']} ({t})\nURL: {SITE_URL}/{url_of(r)}\nJSON: {SITE_URL}/api/{t}/{r['id']}.json\nid: {r['id']}")
            if n.get("aliases"):
                out.append("aliases: " + " · ".join(n["aliases"]))
            if n.get("said"):
                out.append("said: " + n["said"])
            et = r.get("etymology") or {}
            if et.get("root"):
                out.append(f"root: {et['root']}" + (f" · first seen: {et['first_attested']}" if et.get("first_attested") else "") + (f" · {et['note']}" if et.get("note") else ""))
            if r.get("facets"):
                out.append("facets: " + " · ".join(f"{k}={', '.join(map(str, v)) if isinstance(v, list) else v}" for k, v in r["facets"].items()))
            out.append("region: " + ", ".join(t2.get("name", t2["key"]) for t2 in r["region_terms"]))
            for k in ("what", "story", "how", "today", "notes"):
                if r["text"].get(k):
                    out.append(f"{k}: {r['text'][k]}")
            a = r.get("address") or {}
            if a:
                out.append("address: " + ", ".join(x for x in (a.get("street"), a.get("city"), a.get("state"), a.get("postcode")) if x))
            if r.get("geo"):
                out.append(f"geo: {r['geo']['lat']}, {r['geo']['lon']} ({r['geo'].get('precision', '')})")
            for k in r.get("kin_out", []):
                out.append(f"- kin → {k['to']} ({k['type']}): {k['as']}")
            for c in r.get("confusable_with", []):
                out.append(f"- not to be confused with {c['id']}: {c['tell']}")
            for im in r.get("images", []):
                out.append(f"- image: {SITE_URL}/images/{im['file']} · {im.get('license', '')} · {im.get('author', '')} · {im.get('page_url', '')}")
            out.append("sources: " + "; ".join(f"{s} — {sources[s].get('title', '')}" for s in r.get("sources", []) if s in sources))
            out.append(f"provenance default: {r['provenance']['default'].get('tier')} · confidence: {r['confidence']} · needs_verification: {r.get('needs_verification', False)} · updated: {r['updated']}\n")
    return "\n".join(out)


def sitemap(recs: list[dict]) -> str:
    today = time.strftime("%Y-%m-%d")
    urls = [(SITE_URL + "/", max((r["updated"] for r in recs), default=today)), (SITE_URL + "/search/", today), (SITE_URL + "/places/", today),
            (SITE_URL + "/near/", today), (SITE_URL + "/donut/", today), (SITE_URL + "/dough/", today), (SITE_URL + "/counter/", today), (SITE_URL + "/quiz/", today),
            (SITE_URL + "/make/", today), (SITE_URL + "/numbers/", today), (SITE_URL + "/art/", today), (SITE_URL + "/stories/", today),
            (SITE_URL + "/sources/", today), (SITE_URL + "/coverage/", today)] + [(f"{SITE_URL}/{DIR_OF[t]}/", today) for t in TYPES]
    body = []
    for u, d in urls:
        body.append(f"<url><loc>{E(u)}</loc><lastmod>{E(d)}</lastmod></url>")
    for r in recs:
        imgs = "".join(f"<image:image><image:loc>{E(SITE_URL + '/images/' + im['file'])}</image:loc><image:caption>{E(r['names']['name'])}</image:caption>" +
                       (f"<image:license>{E(im['license_url'])}</image:license>" if im.get("license_url") else "") + "</image:image>" for im in r.get("images", []))
        body.append(f"<url><loc>{E(SITE_URL + '/' + url_of(r))}</loc><lastmod>{E(r['updated'])}</lastmod>{imgs}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">' + "".join(body) + "</urlset>\n")


def ai_txt() -> str:
    return (f"# {SITE_NAME} — {SITE_URL}/\n"
            "# Everything here is meant to be read by machines as well as people.\n\n"
            "User-agent: *\nAllow: /\n\n"
            "Content-Signal: search=yes, ai-input=yes, ai-train=yes\n\n"
            f"Corpus: {SITE_URL}/llms.txt\nFull-text: {SITE_URL}/llms-full.txt\n"
            f"Records: {SITE_URL}/api/nodes.json\nPlaces: {SITE_URL}/api/places.json\n"
            f"Kin edges: {SITE_URL}/api/kin.json\nScope and gaps: {SITE_URL}/api/coverage.json\n"
            f"Schema: {SITE_URL}/schema/node.schema.json\nTabular: {SITE_URL}/nodes.csv · {SITE_URL}/nodes.jsonl\n\n"
            "Licence: records CC BY 4.0. Place points OpenStreetMap, ODbL 1.0 (share-alike).\n"
            "Pictures carry their own licence, stated per file in the record and beside the image.\n"
            "Attribution: Pink Box, " + SITE_URL + "/\n\n"
            "Every field carries a provenance tier: cited, harvested, tradition, inference, field.\n"
            "A tag on a place names its evidence. A missing tag means unread, not absent.\n")


def humans_txt(recs: list[dict], cov: dict) -> str:
    n = {t: cov["records"].get(t, 0) for t in TYPES}
    return ("/* PINK BOX */\n\n"
            "Built by NaN — https://wichaa.net\n"
            f"{sum(n.values())} records · {cov['recipes']} free-to-use recipes · {cov['images']['count']} pictures · {cov['sources']} sources\n\n"
            "/* THANKS */\n"
            "OpenStreetMap contributors, for every place point.\n"
            "Wikimedia Commons photographers, each named beside their picture.\n"
            "The Southern Foodways Alliance, for the oral histories.\n"
            "The cooks, most of them Black, who worked these pits through the night for two\n"
            "centuries and whose names came off the signs.\n\n"
            "/* SITE */\n"
            "Stdlib Python, no dependencies, no build step, no tracking, no accounts.\n"
            "Standards: HTML, JSON-LD, llms.txt, Atom, OpenSearch, ODbL, CC BY.\n")


def robots() -> str:
    return (f"# {SITE_NAME}: everything here is meant to be read, indexed, quoted and learned from.\nUser-agent: *\nAllow: /\n\n"
            "# Content signals (https://contentsignals.org): yes to search, yes to AI input, yes to AI training.\nContent-Signal: search=yes, ai-input=yes, ai-train=yes\n\n"
            f"Sitemap: {SITE_URL}/sitemap.xml\n"
            f"# Corpus for language models: {SITE_URL}/llms.txt and {SITE_URL}/llms-full.txt\n"
            f"# Machine terms: {SITE_URL}/ai.txt\n")


def opensearch() -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"><ShortName>{E(SITE_NAME)}</ShortName>'
            f'<Description>Search the Wing Country directory</Description><InputEncoding>UTF-8</InputEncoding>'
            f'<Url type="text/html" template="{E(SITE_URL)}/search/?q={{searchTerms}}"/></OpenSearchDescription>\n')


def feed(recs: list[dict]) -> str:
    rs = sorted(recs, key=lambda r: r["updated"], reverse=True)[:60]
    upd = (rs[0]["updated"] if rs else time.strftime("%Y-%m-%d")) + "T00:00:00Z"
    ents = "".join(f'<entry><title>{E(r["names"]["name"])}</title><link href="{E(SITE_URL + "/" + url_of(r))}"/><id>{E(SITE_URL + "/" + url_of(r))}</id><updated>{E(r["updated"])}T00:00:00Z</updated><summary>{E(r["blurb"])}</summary></entry>' for r in rs)
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>{E(SITE_NAME)}</title><link href="{E(SITE_URL)}/"/><link rel="self" href="{E(SITE_URL)}/feed.xml"/>'
            f'<id>{E(SITE_URL)}/</id><updated>{upd}</updated><author><name>NaN</name></author>{ents}</feed>\n')


def dumps(recs: list[dict]):
    rows = []
    for r in recs:
        f = r.get("facets") or {}
        a = r.get("address") or {}
        g = r.get("geo") or {}
        rows.append({"id": r["id"], "type": r["type"], "name": r["names"]["name"], "aliases": "|".join(r["names"].get("aliases", [])), "region": "|".join(r["region"]),
                     "state": f.get("state") or a.get("state", ""), "city": a.get("city", ""), "lat": g.get("lat", ""), "lon": g.get("lon", ""),
                     "facets": json.dumps(f, ensure_ascii=False) if f else "", "what": r["text"]["what"], "root": (r.get("etymology") or {}).get("root", ""),
                     "kin": "|".join(k["to"] for k in r.get("kin_out", [])), "sources": "|".join(r.get("sources", [])), "tier": r["provenance"]["default"].get("tier", ""),
                     "confidence": r["confidence"], "needs_verification": r.get("needs_verification", False), "updated": r["updated"], "url": f"{SITE_URL}/{url_of(r)}"})
    with open(SITE / "nodes.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["id"])
        w.writeheader()
        w.writerows(rows)
    with open(SITE / "nodes.jsonl", "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps({k: v for k, v in r.items() if k not in ("tiers",)}, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ main

def main() -> int:
    if not (API / "nodes.json").exists():
        print("run tools/build.py first")
        return 1
    t0 = time.time()
    recs = jload(API / "nodes.json")["nodes"]
    by_id = {r["id"]: r for r in recs}
    sources = {s["id"]: s for s in jload(API / "sources.json")["sources"]}
    places = jload(API / "places.json")
    global PLACE_DAYS
    PLACE_DAYS = {p["id"]: p.get("days") or {} for p in places["places"]}
    types = jload(API / "vocab" / "types.json")
    cov = jload(API / "coverage.json")
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    shutil.copytree(API, SITE / "api")
    shutil.copytree(ROOT / "schema", SITE / "schema")
    (SITE / "vendor").mkdir()
    core_js = VENDOR / "searchcore.js"
    if not core_js.exists():
        print("vendor/searchcore.js missing — run search-core/sync.py")
        return 1
    shutil.copy(core_js, SITE / "vendor" / "searchcore.js")
    # Pictures: only the files records name, and never at archive size. A 2 MB scan of a
    # 1944 news photograph is the right thing to keep in data/; it is the wrong thing to
    # send down a phone line. Originals stay put; the published copy is capped at 1600px.
    saved = 0
    for r in recs:
        for im in r.get("images", []):
            src = IMAGES / im["file"]
            if not src.exists():
                continue
            dst = SITE / "images" / im["file"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                from PIL import Image as _Im
                with _Im.open(src) as pic:
                    if max(pic.size) > 1600 or src.stat().st_size > 600_000:
                        pic = pic.convert("RGB")
                        pic.thumbnail((1600, 1600), _Im.LANCZOS)
                        pic.save(dst, "JPEG", quality=84, optimize=True, progressive=True)
                        saved += src.stat().st_size - dst.stat().st_size
                        continue
            except Exception:  # noqa: BLE001
                pass
            shutil.copy(src, dst)
    # pages
    (SITE / "index.html").write_text(front_page(recs, by_id, places, types, cov), encoding="utf-8")
    (SITE / "wander.html").write_text(wander_page(recs), encoding="utf-8")
    for t in types["entries"]:
        d = SITE / DIR_OF[t["key"]]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(art_index(t, recs) if t["key"] == "art" else type_index(t, recs, by_id), encoding="utf-8")
    for r in recs:
        d = SITE / url_of(r)
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(node_page(r, by_id, sources), encoding="utf-8")
    global TAGV
    TAGV = {e["key"]: e for e in jload(DATA / "vocab" / "tags.json")["entries"]}
    (SITE / "places").mkdir(exist_ok=True)
    (SITE / "places" / "index.html").write_text(places_page(places, by_id, recs), encoding="utf-8")
    (SITE / "sources").mkdir(exist_ok=True)
    (SITE / "sources" / "index.html").write_text(sources_page(sources), encoding="utf-8")
    (SITE / "coverage").mkdir(exist_ok=True)
    (SITE / "coverage" / "index.html").write_text(coverage_page(cov), encoding="utf-8")
    # question pages
    tagvocab = jload(DATA / "vocab" / "tags.json")
    donuts = jload(API / "donuts.json") if (API / "donuts.json").exists() else {}
    geo = jload(GEO / "states.json")
    global GEO_CACHE
    GEO_CACHE = geo
    usda = jload(HARVEST / "usda-donuts.json") if (HARVEST / "usda-donuts.json").exists() else {}
    for name, html_text in (("near", pages.near_page(page, places, recs, tagvocab, SITE_URL)),
                            ("donut", pages.donut_page(page, donuts, recs, geo, SITE_URL, usda)),
                            ("dough", pages.dough_page(page, by_id, SITE_URL)),
                            ("counter", pages.counter_page(page, places, recs, tagvocab, geo, SITE_URL)),
                            ("quiz", pages.quiz_page(page, jload(DATA / "vocab" / "quiz.json"), by_id, SITE_URL)),
                            ("numbers", pages.numbers_page(page, recs, places, geo, SITE_URL, SITE)),
                            ("make", pages.make_page(page, jload(DATA / "vocab" / "glaze-builder.json"), donuts, recs, SITE_URL,
                                            jload(DATA / "vocab" / "dough-builder.json"),
                                            jload(DATA / "vocab" / "filling-builder.json")))):
        d = SITE / name
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(html_text, encoding="utf-8")

    # search: docs + tables (fleet hand thesaurus + this project's mined table), fetched by the search page only
    docs = jload(BUILD / "searchdocs.json")["docs"]
    (SITE / "search").mkdir(exist_ok=True)
    (SITE / "search" / "index.html").write_text(search_page(docs), encoding="utf-8")
    groups = []
    # only this project's mined table: the fleet hand table is Thai/medical and would be noise here
    p = DATA / "search" / "wings.thesaurus.json"
    if p.exists():
        groups += jload(p).get("groups", [])
    (SITE / "search" / "tables.json").write_text(json.dumps({"groups": groups, "words": []}, ensure_ascii=False), encoding="utf-8")
    # bot layer
    (SITE / "llms.txt").write_text(llms_txt(recs, cov), encoding="utf-8")
    (SITE / "llms-full.txt").write_text(llms_full(recs, sources), encoding="utf-8")
    (SITE / "sitemap.xml").write_text(sitemap(recs), encoding="utf-8")
    (SITE / "robots.txt").write_text(robots(), encoding="utf-8")
    (SITE / "opensearch.xml").write_text(opensearch(), encoding="utf-8")
    (SITE / "feed.xml").write_text(feed(recs), encoding="utf-8")
    (SITE / "manifest.webmanifest").write_text(manifest(), encoding="utf-8")
    if CARDS_DIR.exists():
        shutil.copytree(CARDS_DIR, SITE / "cards")
    (SITE / "humans.txt").write_text(humans_txt(recs, cov), encoding="utf-8")
    wk = SITE / ".well-known"
    wk.mkdir(exist_ok=True)
    (wk / "ai.txt").write_text(ai_txt(), encoding="utf-8")
    (SITE / "ai.txt").write_text(ai_txt(), encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    (SITE / "icon.svg").write_text(icon_svg(), encoding="utf-8")
    dumps(recs)
    n_html = sum(1 for _ in SITE.rglob("*.html"))
    # privacy gate: no host paths in anything published
    leaks = [p for p in SITE.rglob("*") if p.is_file() and p.suffix in (".html", ".json", ".txt", ".xml", ".csv", ".jsonl") and "/Users/" in p.read_text(encoding="utf-8", errors="ignore")]
    if leaks:
        print("REFUSED: host paths in", [str(p.relative_to(SITE)) for p in leaks][:5])
        return 2
    print(f"site: {n_html} pages · {len(recs)} records · {places.get('independent', places['count'])} independents on the map ({places.get('chains', 0)} chains off) · "
          f"{saved/1e6:.0f} MB saved on pictures · {SITE} · {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
