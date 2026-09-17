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

def shape_of(dm):
    """height over width from a dimensions string: '41.0 x 26.0 cm', or the labelled
    'lehe kõrgus: 28.0 cm; lehe laius: 34.9 cm' MuIS writes for sheets"""
    dm = str(dm or "")
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)", dm)
    if m: a, b = m.group(1), m.group(2)
    else:
        # MuIS labels each measure -- "lehe kõrgus", "graafikaplaadi laius", "kõrgus (raamiga)"
        # -- and a print carries the sheet's and the plate's; pair like with like, the
        # sheet first (it is what the photograph shows), never a plate height with a
        # sheet width
        pairs = {}
        for q, kind, v in re.findall(r"(?:^|;)\s*([^;:]*?)(kõrgus|laius)\s*:\s*(\d+(?:[.,]\d+)?)", dm):
            pairs.setdefault(q.strip(), {})[kind] = v
        pick = next((pairs[q] for q in ("lehe ", "lehe", "", "graafikaplaadi ", "kujutise ") if q in pairs and len(pairs[q]) == 2), None)
        if not pick: pick = next((v for v in pairs.values() if len(v) == 2), None)
        if not pick: return None
        a, b = pick["kõrgus"], pick["laius"]
    b = float(b.replace(",", "."))
    return float(a.replace(",", ".")) / b if b else None

def shard_of(w):
    return str(w["y"] // 10 * 10) if w.get("y") is not None else "und"

index, detail = [], collections.defaultdict(dict)
for i, w in enumerate(W):
    light = {k: v for k, v in w.items() if k not in DETAIL and k != "ir"}
    light["i"] = i                                   # stable handle into the index
    heavy = {k: v for k, v in w.items() if k in DETAIL}
    if heavy:
        light["h"] = 1                               # this record has detail to fetch
        # the wall needs to know which records have a picture before any shard is
        # fetched; the address itself stays in the shard
        if heavy.get("im"):
            light["p"] = 1
            # ...and the tile's shape, height over width from the record's dimensions,
            # so the wall lays out right on the first paint, before the shard arrives
            # the tile takes the photograph's shape -- unless the photograph is taller
            # than the work it shows (a colour chart clipped above the painting, a ruler
            # beneath): then the work's own proportions, and the tile crops from the
            # bottom, so the chart falls off
            rp, rw = w.get("ir"), shape_of(heavy.get("dm"))
            # ...or wider (a chart or ruler at the side): the same, the tile looks at the middle
            off = bool(rp and rw and 0.45 <= rw <= 2.2 and (rp > rw * 1.08 or rp < rw / 1.08))
            r = rw if off else (rp or rw)
            if r: light["r"] = round(min(2.2, max(0.45, r)) * 100)
            if off: light["rc"] = 1
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
