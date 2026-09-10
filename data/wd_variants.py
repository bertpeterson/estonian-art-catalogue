# -*- coding: utf-8 -*-
"""Second pass at Wikidata for artists the exact-name query missed.

The first pass sent each artist's canonical name as an rdfs:label. That fails
whenever our spelling differs from Wikidata's in a way the museums introduced:
brackets carrying an alias — "Gori (Vello Agori)" — or German transliteration,
where we hold "Moeller" and Wikidata holds "Möller". 97 unmatched artists hold
20+ works each. Results are keyed by our canonical name and merged into the
existing tables; merge.py's date-plausibility guard still filters them.
"""
import json, re, time, urllib.parse, urllib.request, unicodedata

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
EP = "https://query.wikidata.org/sparql"
d  = json.load(open("data.json", encoding="utf-8"))
WD  = json.load(open("wd_artists.json", encoding="utf-8"))
WDD = json.load(open("wd_desc.json", encoding="utf-8"))

def variants(n):
    """Spellings Wikidata might hold for a name the museums wrote our way."""
    out, base = [], n.strip()
    bare = re.sub(r"\s*\([^)]*\)\s*", " ", base)
    bare = re.sub(r"\s+", " ", bare).strip()
    for v in (base, bare):
        if not v or len(v) < 4: continue
        out.append(v)
        # German transliteration, both directions
        for a, b in (("oe","ö"), ("ae","ä"), ("ue","ü")):
            if a in v.lower(): out.append(re.sub(a, b, v, flags=re.I))
            if b in v.lower(): out.append(re.sub(b, a, v, flags=re.I))
        # the alias inside the brackets is sometimes the name Wikidata uses
        m = re.search(r"\(([^)]{4,40})\)", base)
        if m and " " in m.group(1): out.append(m.group(1).strip())
    seen, uniq = set(), []
    for v in out:
        if v.lower() not in seen: seen.add(v.lower()); uniq.append(v)
    return uniq[:5]

todo = {}
SKIP = re.compile(r"^(tundmat|teadmata|anon|rühmitus|pseud)", re.I)
for a in d["artists"]:
    if a.get("qid") or not a.get("c") or SKIP.match(a["n"]) or len(a["n"]) < 5: continue
    vs = [v for v in variants(a["n"]) if v != a["n"]]
    if vs: todo[a["n"]] = vs
print(f"artists to retry: {len(todo):,}  ({sum(len(v) for v in todo.values()):,} name variants)", flush=True)

def q(pairs):
    vals = " ".join('"%s"@en' % v.replace("\\", "").replace('"', "") for _, v in pairs)
    query = """SELECT ?name ?p ?desc ?birth ?cLabel ?bLabel WHERE {
  VALUES ?name { %s }
  ?p rdfs:label ?name . ?p wdt:P31 wd:Q5 .
  OPTIONAL { ?p schema:description ?desc . FILTER(lang(?desc)="en") }
  OPTIONAL { ?p wdt:P569 ?birth }
  OPTIONAL { ?p wdt:P27 ?c } OPTIONAL { ?p wdt:P19 ?b }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}""" % vals
    for k in range(3):
        try:
            req = urllib.request.Request(EP, urllib.parse.urlencode({"query": query}).encode(),
                                         {"User-Agent": UA, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())["results"]["bindings"]
        except Exception:
            if k == 2: return []
            time.sleep(5 * (k + 1))
    return []

flat = [(canon, v) for canon, vs in todo.items() for v in vs]
back = {}
for canon, v in flat: back.setdefault(v.lower(), canon)
added_w = added_d = 0
B = 50
for i in range(0, len(flat), B):
    for row in q(flat[i:i+B]):
        v = row["name"]["value"]; canon = back.get(v.lower())
        if not canon: continue
        qid = row["p"]["value"].rsplit("/", 1)[-1]
        by = re.match(r"^(\d{4})", row.get("birth", {}).get("value", "") or "")
        if canon not in WD:
            WD[canon] = {"cit": [row["cLabel"]["value"]] if "cLabel" in row else [], "eth": [],
                         "born": row.get("bLabel", {}).get("value"), "byear": by.group(1) if by else None,
                         "qid": qid}
            added_w += 1
        if canon not in WDD and "desc" in row:
            WDD[canon] = {"desc": row["desc"]["value"], "qid": qid, "byear": by.group(1) if by else None}
            added_d += 1
    if (i // B) % 5 == 0: print(f"  {i+B}/{len(flat)}  +{added_w} ids", flush=True)
    time.sleep(1)

json.dump(WD,  open("wd_artists.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(WDD, open("wd_desc.json",    "w", encoding="utf-8"), ensure_ascii=False)
print(f"\nRECOVERED {added_w} identities, {added_d} descriptions")
