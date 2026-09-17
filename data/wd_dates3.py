# -*- coding: utf-8 -*-
"""A third Wikidata pass for the artists still undated -> wd_matches3.json

wd_dates.py matched on the name and anchored on the years of an artist's works,
and asked for three dated works before it would try. What is left is mostly artists
with one or two dated works, or none, where a name alone is too little to match on.
This pass asks Wikidata for one more thing -- a tie to Estonia -- and then accepts
artists with a single dated work, or, with no dated work at all, a name that
resolves to exactly one Estonian-tied artist of any plausible date.

A candidate must be a person with an artist's occupation AND be tied to Estonia:
citizen of Estonia, the Russian Empire or the Soviet Union (P27), born in a place
in Estonia (P19 -> P17 Q191), or with an Estonian Wikipedia article. With a dated
work, birth must be 10-90 years before the earliest and death not before the median.
Ambiguity rejects, as before. The output has the shape merge.py already reads.
"""
import json, re, time, urllib.parse, urllib.request, statistics, os
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
ART_OCC = {"Q1028181", "Q1281618", "Q11569986", "Q1925963", "Q483501", "Q33231", "Q42973", "Q644687", "Q15296811",
           "Q3391743", "Q329439", "Q7541856", "Q1305237", "Q5322166", "Q3658608", "Q1708232", "Q10862983", "Q2914170",
           "Q15214752", "Q2519376", "Q627325", "Q1114448", "Q2306091", "Q10800557", "Q13365770"}   # + cartoonist, sculptor-medallist, art historian? no: + graphic artist variants
EST = {"Q191", "Q34266", "Q15180", "Q211"}      # Estonia, Russian Empire, Soviet Union, Latvia? no -- Latvia out
EST.discard("Q211")

work_years = {}
for w in W:
    if w.get("y") and not w.get("f"): work_years.setdefault(w["a"], []).append(w["y"])
prev = set(json.load(open("wd_matches2.json", encoding="utf-8")).keys()) if os.path.exists("wd_matches2.json") else set()
cands = [(i, a) for i, a in enumerate(A)
         if not a.get("qid") and not (a.get("l") or [""])[0] and a["n"] not in prev
         and len(a["n"]) > 3 and len(a["n"].split()) >= 2
         and not re.match(r'^(tundmat|teadmata|anon|rühmitus|autor)', a["n"], re.I)
         and not re.match(r'^[A-ZÕÄÖÜ]\.\s', a["n"])]
print(f"pass 3: {len(cands)} undated, unmatched artists", flush=True)

def strip_brackets(n): return re.sub(r'\s*\([^)]*\)', "", n).strip()
matches, rej = {}, {"occupation": 0, "estonia": 0, "years": 0, "ambiguous": 0, "none": 0}
B = 40
for i in range(0, len(cands), B):
    batch = cands[i:i+B]
    names = sorted({strip_brackets(a["n"]) for _, a in batch})
    vals = " ".join('"%s"@%s' % (n.replace('\\', '').replace('"', ''), lang) for n in names for lang in ("et", "en", "de", "ru"))
    rows = sparql("""SELECT ?name ?p ?occ ?b ?d ?desc ?cit ?bpc ?etwiki WHERE {
      VALUES ?name { %s }
      { ?p rdfs:label ?name } UNION { ?p skos:altLabel ?name }
      ?p wdt:P31 wd:Q5 .
      OPTIONAL { ?p wdt:P106 ?occ }
      OPTIONAL { ?p wdt:P569 ?b } OPTIONAL { ?p wdt:P570 ?d }
      OPTIONAL { ?p wdt:P27 ?cit }
      OPTIONAL { ?p wdt:P19 ?bp . ?bp wdt:P17 ?bpc }
      OPTIONAL { ?etwiki schema:about ?p ; schema:isPartOf <https://et.wikipedia.org/> }
      OPTIONAL { ?p schema:description ?desc FILTER(lang(?desc) = "en") }
    }""" % vals)
    by_name = {}
    for r in rows:
        n = r["name"]["value"]; q = r["p"]["value"].rsplit("/", 1)[-1]
        rec = by_name.setdefault(n, {}).setdefault(q, {"occ": set(), "b": None, "d": None, "desc": None, "est": False})
        if "occ" in r: rec["occ"].add(r["occ"]["value"].rsplit("/", 1)[-1])
        b, dd = yr4(r.get("b", {}).get("value")), yr4(r.get("d", {}).get("value"))
        if b and (rec["b"] is None or b < rec["b"]): rec["b"] = b
        if dd and (rec["d"] is None or dd > rec["d"]): rec["d"] = dd
        if "desc" in r and not rec["desc"]: rec["desc"] = r["desc"]["value"]
        if r.get("cit", {}).get("value", "").rsplit("/", 1)[-1] in EST: rec["est"] = True
        if r.get("bpc", {}).get("value", "").rsplit("/", 1)[-1] == "Q191": rec["est"] = True
        if "etwiki" in r: rec["est"] = True
    for idx, a in batch:
        n = strip_brackets(a["n"]); items = by_name.get(n, {})
        if not items: rej["none"] += 1; continue
        ys = sorted(work_years.get(idx, []))
        ok = []
        for q, rec in items.items():
            if not (rec["occ"] & ART_OCC): rej["occupation"] += 1; continue
            if not rec["est"]: rej["estonia"] += 1; continue
            if rec["b"] is None: rej["years"] += 1; continue
            if ys:
                first, med = ys[0], int(statistics.median(ys))
                if not (10 <= first - rec["b"] <= 90): rej["years"] += 1; continue
                if rec["d"] is not None and med > rec["d"] + 1: rej["years"] += 1; continue
            elif not (1500 <= rec["b"] <= 2005): rej["years"] += 1; continue
            ok.append((q, rec))
        if len(ok) == 1:
            q, rec = ok[0]
            matches[a["n"]] = {"qid": q, "byear": rec["b"], "dyear": rec["d"], "desc": rec["desc"], "anchor": ys[:1] + ([int(statistics.median(ys))] if ys else [])}
        elif len(ok) > 1: rej["ambiguous"] += 1
    print(f"  {min(i+B, len(cands))}/{len(cands)}  matched {len(matches)}", flush=True)
    time.sleep(1.0)
prev3 = json.load(open("wd_matches3.json", encoding="utf-8")) if os.path.exists("wd_matches3.json") else {}
prev3.update(matches); matches = prev3   # a rerun adds to the file, never replaces it
json.dump(matches, open("wd_matches3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"\nPASS 3: matched {len(matches)} of {len(cands)}; rejected {rej}")
for n, m in list(matches.items())[:8]: print("  ", n, m["byear"], m["dyear"], "|", (m["desc"] or "")[:50])
