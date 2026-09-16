# -*- coding: utf-8 -*-
"""Build the self-hosted static site: a light index loaded once, plus per-decade
detail shards fetched only when a record is opened. Nothing is dropped."""
import json, os, shutil, collections

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

def shard_of(w):
    return str(w["y"] // 10 * 10) if w.get("y") is not None else "und"

index, detail = [], collections.defaultdict(dict)
for i, w in enumerate(W):
    light = {k: v for k, v in w.items() if k not in DETAIL}
    light["i"] = i                                   # stable handle into the index
    heavy = {k: v for k, v in w.items() if k in DETAIL}
    if heavy:
        light["h"] = 1                               # this record has detail to fetch
        detail[shard_of(w)][str(i)] = heavy
    index.append(light)

meta = dict(d["meta"])
meta["shards"] = sorted(detail.keys())
json.dump({"meta": meta, "artists": A, "vocab": d.get("vocab", {}), "works": index},
          open(f"{OUT}/data/index.json", "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
for k, v in detail.items():
    json.dump(v, open(f"{OUT}/data/detail/{k}.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
shutil.copy("i18n.json", f"{OUT}/data/i18n.json")

ix = os.path.getsize(f"{OUT}/data/index.json")
ds = sum(os.path.getsize(f"{OUT}/data/detail/{f}") for f in os.listdir(f"{OUT}/data/detail"))
print(f"index.json      {ix/1048576:.2f} MB")
print(f"detail shards   {ds/1048576:.2f} MB across {len(detail)} files")
print(f"largest shard   {max(os.path.getsize(f'{OUT}/data/detail/{f}') for f in os.listdir(f'{OUT}/data/detail'))/1024:.0f} KB")
print(f"records with detail: {sum(len(v) for v in detail.values()):,} of {len(W):,}")
