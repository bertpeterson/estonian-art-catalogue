# -*- coding: utf-8 -*-
"""Flat exports of the catalogue, for people who do not want to decode our JSON.

data.json is dictionary-encoded and nested, which is right for the site and wrong
for anyone with a spreadsheet. These write one row per work with every value
resolved, plus a separate artist table.
"""
import json, csv, gzip, os

d = json.load(open("data.json", encoding="utf-8"))
A, W, V = d["artists"], d["works"], d.get("vocab", {})
os.makedirs("../site/data/export", exist_ok=True)

def val(w, f):
    v = w.get(f)
    if isinstance(v, int) and f in V: return V[f][v] if 0 <= v < len(V[f]) else None
    return v

COLS = [("artist",   lambda w: A[w["a"]]["n"]),
        ("title",    lambda w: w.get("t")),
        ("year",     lambda w: w.get("y")),
        ("date_as_recorded", lambda w: w.get("yl")),
        ("type",     lambda w: val(w, "e")),
        ("technique",lambda w: val(w, "tc") or val(w, "tce")),
        ("material", lambda w: val(w, "m")  or val(w, "me")),
        ("dimensions", lambda w: w.get("dm")),
        ("holder",   lambda w: val(w, "mu")),
        ("collection", lambda w: val(w, "co")),
        ("inventory_no", lambda w: w.get("nu")),
        ("kind",     lambda w: w.get("kind", "held")),
        ("source",   lambda w: val(w, "s")),
        ("muis_id",  lambda w: w.get("mi")),
        ("ekm_id",   lambda w: w.get("oi")),
        ("url",      lambda w: w.get("url")),
        ("objects_merged", lambda w: w.get("n", 1))]

with gzip.open("../site/data/export/works.csv.gz", "wt", encoding="utf-8", newline="") as f:
    wr = csv.writer(f); wr.writerow([c for c, _ in COLS])
    for w in W: wr.writerow([g(w) for _, g in COLS])

ACOLS = [("name", "n"), ("born", None), ("died", None), ("works", "c"),
         ("birthplace", "born"), ("affiliation", "aff"), ("wikidata", "qid"),
         ("wikidata_description", "wdesc")]
with gzip.open("../site/data/export/artists.csv.gz", "wt", encoding="utf-8", newline="") as f:
    wr = csv.writer(f); wr.writerow([c for c, _ in ACOLS])
    for a in A:
        life = a.get("l") or ["", ""]
        wr.writerow([a.get("n"), life[0], life[1], a.get("c", 0),
                     a.get("born"), a.get("aff"), a.get("qid"), a.get("wdesc")])

# one JSON object per line, for stream processing
with gzip.open("../site/data/export/works.jsonl.gz", "wt", encoding="utf-8") as f:
    for w in W:
        f.write(json.dumps({c: g(w) for c, g in COLS}, ensure_ascii=False) + "\n")

for n in ("works.csv.gz", "artists.csv.gz", "works.jsonl.gz"):
    print(f"  site/data/export/{n:18} {os.path.getsize('../site/data/export/'+n)/1048576:5.2f} MB")
print(f"\n{len(W):,} works, {len(A):,} artists exported")
