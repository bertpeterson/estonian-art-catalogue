# -*- coding: utf-8 -*-
"""Build the self-hosted static site: a light index loaded once, plus per-decade
detail shards fetched only when a record is opened. Nothing is dropped."""
import re, json, os, shutil, collections

SRC = "data/data.json"
OUT = "site"
# Only rendered inside an opened record. Everything else has to stay in the index:
# the search haystack is built from technique, material, inventory number, collection,
# category and date label, so moving those out would silently empty those searches.
# mi/oi/url only ever build the "source record" links in the detail panel.
# url stays in the index: a gallery row links to the gallery from the list itself,
# before any shard is fetched. 4,222 short strings, about 250 KB.
DETAIL = {"d", "de", "dm", "mem", "mi", "oi", "im"}

d = json.load(open(SRC, encoding="utf-8"))
W, A = d["works"], d["artists"]

# the six similar artists (data/similar.py) live beside the dataset, not in it
if os.path.exists("data/similar.json"):
    for _i, _s in json.load(open("data/similar.json", encoding="utf-8")).items(): A[int(_i)]["sim"] = _s

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(f"{OUT}/data/detail", exist_ok=True)

# static/ is copied in verbatim. The rmtree above removes everything in site/, so
# files that must persist — the Search Console verification file, a CNAME for a
# custom domain — cannot simply be placed there; they live in static/ and land here.
if os.path.isdir("static"):
    for name in os.listdir("static"):
        if name == "README.md": continue
        shutil.copy2(os.path.join("static", name), os.path.join(OUT, name))
        print(f"  static -> site/{name}")

import sys; sys.path.insert(0, "data")
from shape_of import shape_of

def shard_of(w):
    return str(w["y"] // 10 * 10) if w.get("y") is not None else "und"

# works that look like this (data/lookalikes.py): by key there, by position here, into
# the record's shard; and every pictured work's address into pics.json, the one file
# the wall and the look-alike rows read their pictures from
_key = lambda w: w.get("k") or re.sub(r"[^A-Z0-9:]", "", (w.get("nu") or "").upper())
_kidx = {_key(w): i for i, w in enumerate(W) if _key(w)}
LA = {}
if os.path.exists("data/lookalikes.json"):
    for k, ks in json.load(open("data/lookalikes.json", encoding="utf-8")).items():
        if k in _kidx: LA[_kidx[k]] = [_kidx[x] for x in ks if x in _kidx]
pics = {i: w["im"] for i, w in enumerate(W) if w.get("im")}
json.dump(pics, open(f"{OUT}/data/pics.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# the colour charts data/chart_side.py found in the museums' photographs: {picture: [side, fraction]}
CHARTS = {k: v for k, v in (json.load(open("data/chart_sides.json", encoding="utf-8")) if os.path.exists("data/chart_sides.json") else {}).items() if v}

index, detail = [], collections.defaultdict(dict)
for i, w in enumerate(W):
    # the light record: nothing that is null, nothing the reader can infer -- the
    # position is the handle (w.i is set at load), a count of one is the default, a
    # dating label equal to the year is the year. A fifth of the file, gone.
    light = {k: v for k, v in w.items() if k not in DETAIL and k != "ir" and v is not None}
    if light.get("n") == 1: light.pop("n")
    if "yl" in light and str(light["yl"]) == str(light.get("y")): light.pop("yl")
    heavy = {k: v for k, v in w.items() if k in DETAIL}
    if LA.get(i): heavy["la"] = LA[i]
    if heavy:
        light["h"] = 1                               # this record has detail to fetch
        # the wall needs to know which records have a picture before any shard is
        # fetched; the address itself stays in the shard
        if heavy.get("im"):
            light["p"] = 1
            # ...and the tile's shape, height over width, so the wall lays out right on
            # the first paint: the photograph's own shape, or the record's dimensions
            # when the photograph's is unknown. Where data/chart_side.py found a colour
            # chart along one edge, the tile and the record show the photograph less
            # that band -- rs says which side, rf how much of the width or height -- and
            # the shape is the photograph's without it.
            rp, rw = w.get("ir"), shape_of(heavy.get("dm"))
            ch = CHARTS.get(heavy["im"])
            r = rp or rw
            if ch and rp:
                side, f = ch
                r = rp / (1 - f) if side in "lr" else rp * (1 - f)
                light["rs"] = side; light["rf"] = round(f * 100)
            if r: light["r"] = round(min(2.2, max(0.45, r)) * 100)
        detail[shard_of(w)][str(i)] = heavy
    index.append(light)

meta = dict(d["meta"])
meta["shards"] = sorted(detail.keys())
# The biographies leave the index. They are read only on an artist's own page, in an
# opened record and in the artist-grouped list, yet every visitor downloaded all 896
# of them -- 0.44 MB of the 3.3 MB gzipped index -- before the catalogue would answer.
# bios.json holds them by artist position (0 where there is none); the app fetches it
# when it first needs a biography, and on idle after the landing page has painted.
BIO = {"b", "ben", "bs", "bens", "bmt", "wdesc"}
A_light = [{k: v for k, v in a.items() if k not in BIO} for a in A]
bios = [{k: v for k, v in a.items() if k in BIO and k != "bs"} or 0 for a in A]
for i, a in enumerate(A):
    if bios[i] and a.get("bs"): bios[i]["bs"] = a["bs"]
json.dump({"meta": meta, "artists": A_light, "vocab": d.get("vocab", {}), "works": index, "upcoming": d.get("upcoming", [])},
          open(f"{OUT}/data/index.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
json.dump(bios, open(f"{OUT}/data/bios.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
for k, v in detail.items():
    json.dump(v, open(f"{OUT}/data/detail/{k}.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
shutil.copy("i18n.json", f"{OUT}/data/i18n.json")

ix = os.path.getsize(f"{OUT}/data/index.json")
ds = sum(os.path.getsize(f"{OUT}/data/detail/{f}") for f in os.listdir(f"{OUT}/data/detail"))
print(f"index.json      {ix/1048576:.2f} MB")
print(f"bios.json       {os.path.getsize(f'{OUT}/data/bios.json')/1048576:.2f} MB")
print(f"pics.json       {os.path.getsize(f'{OUT}/data/pics.json')/1048576:.2f} MB, {len(pics):,} pictures; look-alikes for {len(LA):,} works; "
      f"{sum(1 for l in index if l.get('rs')):,} tiles cropped of a colour chart")
print(f"detail shards   {ds/1048576:.2f} MB across {len(detail)} files")
print(f"largest shard   {max(os.path.getsize(f'{OUT}/data/detail/{f}') for f in os.listdir(f'{OUT}/data/detail'))/1024:.0f} KB")
print(f"records with detail: {sum(len(v) for v in detail.values()):,} of {len(W):,}")
