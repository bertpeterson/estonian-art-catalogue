# -*- coding: utf-8 -*-
"""Life dates from Wikidata, for the artists the museums left undated.

Two passes. The first takes every artist already matched to a Wikidata item and
fetches birth and death (P569, P570): 514 of them had a match but no dates, because
merge.py used Wikidata's birth year only to check a match, never to fill one.

The second tries to match the artists who have neither a match nor a date, and it
is the risky one: Wikidata is matched on the name, and names collide. The earlier
passes anchored on the museum's dates, which these artists do not have. The anchor
here is what the catalogue does know -- the years of their works. A candidate is
accepted only if it is a person with an artist's occupation, born between ten and
ninety years before the artist's earliest dated work, not dead before the median
one, and the only candidate that passes. One survivor or nothing.

Writes wd_dates.json {qid: [birth, death]} and wd_matches2.json {name: {...}}.
"""
import json, re, time, urllib.parse, urllib.request, statistics
UA = "EstonianArtCatalogue/1.0 (one-off research compile; contact via claude.ai)"
EP = "https://query.wikidata.org/sparql"

def sparql(query):
    for attempt in range(4):
        try:
            req = urllib.request.Request(EP, urllib.parse.urlencode({"query": query}).encode(),
                {"User-Agent": UA, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())["results"]["bindings"]
        except Exception as e:
            if attempt == 3: print("   query failed:", type(e).__name__, flush=True); return []
            time.sleep(5 * (attempt + 1))
    return []

d = json.load(open("data.json", encoding="utf-8"))
A, W = d["artists"], d["works"]
yr4 = lambda s: (lambda m: int(m.group(1)) if m else None)(re.match(r'^[+-]?(\d{4})', str(s or "")))

# ---- pass 1: dates for existing matches -------------------------------------
qids = sorted({a["qid"] for a in A if a.get("qid")})
print(f"pass 1: {len(qids)} matched artists", flush=True)
dates = {}
for i in range(0, len(qids), 200):
    batch = qids[i:i+200]
    rows = sparql("""SELECT ?p ?b ?d WHERE { VALUES ?p { %s }
      OPTIONAL { ?p wdt:P569 ?b } OPTIONAL { ?p wdt:P570 ?d } }""" % " ".join("wd:" + q for q in batch))
    for r in rows:
        q = r["p"]["value"].rsplit("/", 1)[-1]
        b, dd = yr4(r.get("b", {}).get("value")), yr4(r.get("d", {}).get("value"))
        cur = dates.setdefault(q, [None, None])
        # an item can carry several dates; keep the earliest birth and latest death
        if b and (cur[0] is None or b < cur[0]): cur[0] = b
        if dd and (cur[1] is None or dd > cur[1]): cur[1] = dd
    print(f"  {min(i+200, len(qids))}/{len(qids)}", flush=True)
    time.sleep(0.7)
json.dump(dates, open("wd_dates.json", "w", encoding="utf-8"))
print(f"  dates for {sum(1 for v in dates.values() if v[0])} items", flush=True)

# ---- pass 2: guarded matching for the undated, unmatched ----------------------
ART_OCC = {"Q1028181": "painter", "Q1281618": "sculptor", "Q11569986": "printmaker",
           "Q1925963": "graphic artist", "Q483501": "artist", "Q33231": "photographer",
           "Q42973": "architect", "Q644687": "illustrator", "Q15296811": "drawer",
           "Q3391743": "visual artist", "Q329439": "engraver", "Q7541856": "ceramicist",
           "Q1305237": "textile artist", "Q5322166": "designer", "Q3658608": "caricaturist",
           "Q1708232": "medallist", "Q10862983": "lithographer", "Q2914170": "glass artist",
           "Q15214752": "art teacher", "Q2519376": "theatre designer", "Q627325": "graphic designer"}
work_years = {}
for w in W:
    if w.get("y") and not w.get("f"): work_years.setdefault(w["a"], []).append(w["y"])
cands = [(i, a) for i, a in enumerate(A)
         if not a.get("qid") and not (a.get("l") or [""])[0] and (a.get("c") or 0) >= 3
         and i in work_years and len(a["n"]) > 3
         and not re.match(r'^(tundmat|teadmata|anon|rühmitus)', a["n"], re.I)
         and not re.match(r'^[A-ZÕÄÖÜ]\.\s', a["n"])             # "L. Hess": an initial is not a name to match on
         and len(a["n"].split()) >= 2]                              # nor is a mononym
print(f"\npass 2: {len(cands)} undated, unmatched artists with 3+ dated works", flush=True)

def strip_brackets(n): return re.sub(r'\s*\([^)]*\)', "", n).strip()
matches, rejected = {}, {"occupation": 0, "years": 0, "ambiguous": 0, "none": 0}
B = 40
for i in range(0, len(cands), B):
    batch = cands[i:i+B]
    names = sorted({strip_brackets(a["n"]) for _, a in batch})
    vals = " ".join('"%s"@%s' % (n.replace('\\', '').replace('"', ''), lang)
                    for n in names for lang in ("et", "en", "de", "ru", "fr"))
    rows = sparql("""SELECT ?name ?p ?occ ?b ?d ?desc WHERE {
      VALUES ?name { %s }
      { ?p rdfs:label ?name } UNION { ?p skos:altLabel ?name }
      ?p wdt:P31 wd:Q5 .
      OPTIONAL { ?p wdt:P106 ?occ }
      OPTIONAL { ?p wdt:P569 ?b } OPTIONAL { ?p wdt:P570 ?d }
      OPTIONAL { ?p schema:description ?desc FILTER(lang(?desc) = "en") }
    }""" % vals)
    by_name = {}
    for r in rows:
        n = r["name"]["value"]; q = r["p"]["value"].rsplit("/", 1)[-1]
        rec = by_name.setdefault(n, {}).setdefault(q, {"occ": set(), "b": None, "d": None, "desc": None})
        if "occ" in r: rec["occ"].add(r["occ"]["value"].rsplit("/", 1)[-1])
        b, dd = yr4(r.get("b", {}).get("value")), yr4(r.get("d", {}).get("value"))
        if b and (rec["b"] is None or b < rec["b"]): rec["b"] = b
        if dd and (rec["d"] is None or dd > rec["d"]): rec["d"] = dd
        if "desc" in r and not rec["desc"]: rec["desc"] = r["desc"]["value"]
    for idx, a in batch:
        n = strip_brackets(a["n"]); items = by_name.get(n, {})
        if not items: rejected["none"] += 1; continue
        ys = sorted(work_years[idx]); first, med = ys[0], int(statistics.median(ys))
        ok = []
        for q, rec in items.items():
            if not (rec["occ"] & set(ART_OCC)): rejected["occupation"] += 1; continue
            if rec["b"] is None or not (10 <= first - rec["b"] <= 90): rejected["years"] += 1; continue
            if rec["d"] is not None and med > rec["d"] + 1: rejected["years"] += 1; continue
            ok.append((q, rec))
        if len(ok) == 1:
            q, rec = ok[0]
            matches[a["n"]] = {"qid": q, "byear": rec["b"], "dyear": rec["d"], "desc": rec["desc"],
                               "occ": sorted(ART_OCC[o] for o in rec["occ"] if o in ART_OCC),
                               "anchor": [first, med]}
        elif len(ok) > 1: rejected["ambiguous"] += 1
    print(f"  {min(i+B, len(cands))}/{len(cands)}  matched {len(matches)}", flush=True)
    time.sleep(1.0)
json.dump(matches, open("wd_matches2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"\nMATCHED {len(matches)} of {len(cands)}; rejected {rejected}", flush=True)
for n, m in list(matches.items())[:12]:
    print(f"   {n:32} {m['qid']:10} {m['byear']}–{m['dyear'] or ''}  {', '.join(m['occ'])[:30]}  works {m['anchor']}")

# ---- pass 3: occupations for every match ----------------------------------------
# The first passes matched on the name alone, and where the museum had no dates the
# plausibility check had nothing to say. Filling those dates from Wikidata exposed
# what that let through: a footballer born in 2003, a U-boat commander, an actor.
# Occupation is the check that was missing. merge.py drops a match whose item has
# occupations and none of them is an artist's; an item with no occupation is kept.
qids = sorted({a["qid"] for a in A if a.get("qid")} | {m["qid"] for m in matches.values()})
print(f"\npass 3: occupations for {len(qids)} items", flush=True)
occ = {}
for i in range(0, len(qids), 200):
    rows = sparql("SELECT ?p ?o WHERE { VALUES ?p { %s } ?p wdt:P106 ?o }" % " ".join("wd:" + q for q in qids[i:i+200]))
    for r in rows:
        occ.setdefault(r["p"]["value"].rsplit("/", 1)[-1], []).append(r["o"]["value"].rsplit("/", 1)[-1])
    time.sleep(0.7)
json.dump(occ, open("wd_occ.json", "w", encoding="utf-8"))
bad = [q for q, os_ in occ.items() if not (set(os_) & set(ART_OCC))]
print(f"  items with occupations: {len(occ)}; none artistic: {len(bad)}", flush=True)
