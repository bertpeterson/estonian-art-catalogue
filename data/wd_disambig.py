# -*- coding: utf-8 -*-
"""Pick the right Wikidata person when a name has several.

"Paul Raud" is both an Estonian painter (1865-1930) and an Estonian writer (born
1999). The earlier passes kept whichever row arrived last, and merge.py then dropped
the artist entirely when its two passes disagreed — correct when nothing can settle
it, wasteful when something can. The museums record his dates as 1865-1930, which
settles it.

So: for every artist still unmatched but carrying a birth year from a museum, fetch
ALL candidates for the name and keep only one whose birth year agrees within 3 years.
Ambiguity that the dates cannot resolve is still left unresolved.
"""
import json, re, time, urllib.parse, urllib.request

UA = "EstonianArtCatalogue/1.0 (research compile; contact via claude.ai)"
EP = "https://query.wikidata.org/sparql"
d   = json.load(open("data.json", encoding="utf-8"))
WD  = json.load(open("wd_artists.json", encoding="utf-8"))
WDD = json.load(open("wd_desc.json", encoding="utf-8"))

SKIP = re.compile(r"^(tundmat|teadmata|anon|rühmitus|pseud)", re.I)
todo = [a for a in d["artists"]
        if not a.get("qid") and a.get("c") and not SKIP.match(a["n"])
        and (a.get("l") or ["", ""])[0][:4].isdigit()]
print(f"unmatched artists carrying a museum birth year: {len(todo):,}", flush=True)

def q(names):
    vals = " ".join('"%s"@en' % n.replace("\\", "").replace('"', "") for n in names)
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

want = {a["n"]: int(a["l"][0][:4]) for a in todo}
names = list(want)
picked = ambiguous = 0
B = 50
for i in range(0, len(names), B):
    cands = {}
    for row in q(names[i:i+B]):
        n = row["name"]["value"]
        by = re.match(r"^(\d{4})", row.get("birth", {}).get("value", "") or "")
        cands.setdefault(n, []).append({
            "qid": row["p"]["value"].rsplit("/", 1)[-1],
            "byear": by.group(1) if by else None,
            "desc": row.get("desc", {}).get("value"),
            "cit": [row["cLabel"]["value"]] if "cLabel" in row else [],
            "born": row.get("bLabel", {}).get("value")})
    for n, rows in cands.items():
        fit = [r for r in rows if r["byear"] and abs(int(r["byear"]) - want[n]) <= 3]
        # one candidate agreeing with the museum's date, and only one
        if len({r["qid"] for r in fit}) != 1:
            if len(rows) > 1: ambiguous += 1
            continue
        r = fit[0]
        WD[n]  = {"cit": r["cit"], "eth": [], "born": r["born"], "byear": r["byear"], "qid": r["qid"]}
        if r["desc"]: WDD[n] = {"desc": r["desc"], "qid": r["qid"], "byear": r["byear"]}
        picked += 1
    if (i // B) % 6 == 0: print(f"  {min(i+B,len(names))}/{len(names)}  picked {picked}", flush=True)
    time.sleep(1)

json.dump(WD,  open("wd_artists.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(WDD, open("wd_desc.json",    "w", encoding="utf-8"), ensure_ascii=False)
print(f"\nDISAMBIGUATED {picked} artists; {ambiguous} left unresolved (dates could not settle them)")
