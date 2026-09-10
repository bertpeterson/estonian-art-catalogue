# -*- coding: utf-8 -*-
"""Sanity checks over data.json. Run after merge.py; exits non-zero on a real problem.

Every data bug this project has had was found by someone happening to look: a 1964
biologist attached to a 17th-century woodcarver, "1940ndad" filed as undated,
"oil on canvas, 150&#21" left by a truncated HTML entity. These are the cheap
mechanical checks that would have caught them.
"""
import json, re, sys, collections

d = json.load(open("data.json", encoding="utf-8"))
A, W, V = d["artists"], d["works"], d.get("vocab", {})
fail, warn = [], []

def check(cond, msg, hard=True):
    if not cond: (fail if hard else warn).append(msg)

# --- works
check(all(w.get("t") for w in W), "works with an empty title")
bad_year = [w for w in W if w.get("y") is not None and not (1400 <= w["y"] <= 2030)]
check(not bad_year, f"{len(bad_year)} works dated outside 1400-2030: {[w['y'] for w in bad_year[:5]]}")
check(all(isinstance(w.get("a"), int) and 0 <= w["a"] < len(A) for w in W), "works pointing at a missing artist")
ent = [w for w in W if any("&#" in str(w.get(f) or "") for f in ("t","tc","tce","m","me","dm"))]
check(not ent, f"{len(ent)} works with an undecoded HTML entity, e.g. {[w['t'][:40] for w in ent[:3]]}")
# the same rule merge.py excludes on: a bracketed "(?)", or a "?" after a
# capitalised word or closing bracket. Not any trailing "?" — "Chto delat/What is
# to be done?" is a real name, and "(HBK?)" queries a monogram, not the attribution.
UNCERTAIN = re.compile(r'(?:\(\s*\?\s*\)|(?:[A-ZÕÄÖÜŠŽ][^\s]*|\))\s*\?)\s*$')
unc = [w for w in W if UNCERTAIN.search(A[w["a"]]["n"])]
check(not unc, f"{len(unc)} works under an uncertain attribution")

# --- artists
orphan = [a["n"] for a in A if not a.get("c")]
check(not orphan, f"{len(orphan)} artists with no works: {orphan[:5]}")
check(not [a for a in A if not a["n"].strip()], "artists with an empty name")
punct = [a["n"] for a in A if a["n"][:1] in "'\";,.-"]
check(not punct, f"{len(punct)} artist names starting with punctuation: {punct[:5]}")
# a Wikidata description must not contradict the museum's own dates
clash = []
for a in A:
    m = re.search(r'\((?:born\s+)?(\d{4})', a.get("wdesc") or "")
    b = (a.get("l") or ["",""])[0]
    if m and b.isdigit() and abs(int(m.group(1)) - int(b)) > 15:
        clash.append(f"{a['n']}: museum {b} vs {a['wdesc']}")
check(not clash, f"{len(clash)} artists whose Wikidata description contradicts their dates: {clash[:3]}")

# --- counts agree with the data
meta = d["meta"]
check(meta["works"] == len(W), f"meta.works {meta['works']} != {len(W)}")
check(meta["artists"] == len(A), f"meta.artists {meta['artists']} != {len(A)}")
check(meta["undated"] == sum(1 for w in W if w.get("y") is None), "meta.undated disagrees with the works")
kinds = collections.Counter(w.get("kind", "held") for w in W)
check(meta.get("gallery", 0) == kinds["gallery"], "meta.gallery disagrees with the works")

# --- vocab integrity
for f, table in V.items():
    bad = [w for w in W if isinstance(w.get(f), int) and not (0 <= w[f] < len(table))]
    check(not bad, f"{len(bad)} works index outside vocab['{f}']")

for m in warn: print("  warn:", m)
for m in fail: print("  FAIL:", m)
print(f"\n{len(W):,} works, {len(A):,} artists — {'OK' if not fail else str(len(fail))+' problem(s)'}")
sys.exit(1 if fail else 0)
