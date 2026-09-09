# -*- coding: utf-8 -*-
import json, re, time, urllib.parse, urllib.request, unicodedata, collections
UA = "EstonianArtCatalogue/1.0 (one-off research compile; contact via claude.ai)"
EP = "https://query.wikidata.org/sparql"

d = json.load(open('data.json', encoding='utf-8'))
A = [a for a in d['artists'] if a.get('c', 0) > 0]
SKIP = re.compile(r'^(tundmat|teadmata|anon|rühmitus)', re.I)
names = [a['n'] for a in A if not SKIP.match(a['n']) and len(a['n']) > 3]
print(f"artists to resolve: {len(names):,}", flush=True)

def q(batch):
    vals = " ".join('"%s"@en' % n.replace('\\', '').replace('"', '') for n in batch)
    query = """SELECT ?name ?p ?cLabel ?eLabel ?bLabel ?birth WHERE {
  VALUES ?name { %s }
  ?p rdfs:label ?name .
  ?p wdt:P31 wd:Q5 .
  OPTIONAL { ?p wdt:P27 ?c }
  OPTIONAL { ?p wdt:P172 ?e }
  OPTIONAL { ?p wdt:P19 ?b }
  OPTIONAL { ?p wdt:P569 ?birth }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}""" % vals
    for attempt in range(3):
        try:
            req = urllib.request.Request(EP, urllib.parse.urlencode({"query": query}).encode(),
                {"User-Agent": UA, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())["results"]["bindings"]
        except Exception as e:
            if attempt == 2:
                print("   batch failed:", type(e).__name__, flush=True); return []
            time.sleep(4 * (attempt + 1))
    return []

out = {}
B = 60
for i in range(0, len(names), B):
    batch = names[i:i+B]
    for b in q(batch):
        n = b['name']['value']
        rec = out.setdefault(n, {"cit": set(), "eth": set(), "born": None, "byear": None, "qid": None})
        rec["qid"] = b['p']['value'].rsplit('/', 1)[-1]
        if 'cLabel' in b: rec["cit"].add(b['cLabel']['value'])
        if 'eLabel' in b: rec["eth"].add(b['eLabel']['value'])
        if 'bLabel' in b and not rec["born"]: rec["born"] = b['bLabel']['value']
        if 'birth' in b and not rec["byear"]: rec["byear"] = b['birth']['value'][:4]
    if (i // B) % 5 == 0:
        print(f"  {min(i+B,len(names))}/{len(names)}  resolved {len(out):,}", flush=True)
    time.sleep(0.7)

ser = {n: {"cit": sorted(v["cit"]), "eth": sorted(v["eth"]), "born": v["born"],
           "byear": v["byear"], "qid": v["qid"]} for n, v in out.items()}
json.dump(ser, open('wd_artists.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f"\nRESOLVED {len(ser):,} of {len(names):,}  ({len(ser)/len(names)*100:.0f}%)", flush=True)
cit = collections.Counter(c for v in ser.values() for c in v["cit"])
print("top citizenships:", cit.most_common(12), flush=True)
