# -*- coding: utf-8 -*-
"""Refuse a merged dataset that quietly lost records.

    python3 data_guard.py <previous data.json> <new data.json>

harvest_guard.py checks each gallery's harvest before the merge; this checks the merge
itself. A monthly run adds records and retires a few, so small moves are expected. A
drop larger than the thresholds below -- in works, artists, pictured works, museum
holdings or auction lots, or in the works of any of the fifty artists with the most --
means a merge rule or a source went wrong, and the run stops before anything is
committed. Exit 1 with a table of what moved.
"""
import json, sys, collections

LIMIT = 0.03          # a fall of more than 3% in a total
LIMIT_ARTIST = 0.15   # ...or of more than 15% in one of the fifty largest artists

def figures(path):
    d = json.load(open(path, encoding="utf-8"))
    W, A = d["works"], d["artists"]
    kind = lambda w: w.get("kind") or "held"
    per = collections.Counter(A[w["a"]]["n"] for w in W)
    return {"works": len(W), "artists": sum(1 for a in A if a.get("c", 1) > 0),
            "pictured": sum(1 for w in W if w.get("im")),
            "museum holdings": sum(1 for w in W if kind(w) == "held"),
            "auction lots": sum(1 for w in W if kind(w) == "auction")}, per

old, old_per = figures(sys.argv[1])
new, new_per = figures(sys.argv[2])
bad = []
print(f"{'':18}{'before':>10}{'after':>10}{'change':>9}")
for k in old:
    ch = (new[k] - old[k]) / old[k] if old[k] else 0
    flag = ch < -LIMIT
    print(f"{k:18}{old[k]:>10,}{new[k]:>10,}{ch:>+8.1%}{'  <- too large a fall' if flag else ''}")
    if flag: bad.append(k)
for name, n in old_per.most_common(50):
    ch = (new_per.get(name, 0) - n) / n
    if ch < -LIMIT_ARTIST:
        print(f"  {name}: {n:,} -> {new_per.get(name, 0):,} ({ch:+.0%})  <- too large a fall")
        bad.append(name)
if bad:
    print(f"\nDATA GUARD: refused -- {', '.join(bad)} fell further than a monthly run should move them")
    sys.exit(1)
print("\nDATA GUARD: ok")
